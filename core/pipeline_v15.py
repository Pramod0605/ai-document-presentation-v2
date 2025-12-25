"""
Pipeline v1.5 - Split Agent Architecture

Orchestrates the complete V1.5 pipeline with focused agents:
- Pass 0: Smart Chunker (topic extraction) - REUSED from V1.4
- Pass 1: SectionPlanner (section blueprints)
- Pass 2: Per-section loop: NarrationWriter → VisualSpecArtist → RendererSpecAgent (video only)
- Pass 3: MemoryFlashcardAgent + RecapSceneAgent
- Merge Step: Combine all agent outputs into presentation.json
- Pass 4: TTS Duration (generate audio, measure actual duration)
- Pass 5: ManimCodeGenerator (post-TTS, uses actual audio duration for timing)
- Pass 6: Renderers execution (Manim/WAN)

Key improvements:
- Each agent outputs 5-15 fields (vs 50+), enabling per-agent retries
- Manim code generated AFTER TTS with actual audio timing (not estimates)
- Uses Claude Sonnet 4.5 for direct Python code generation with validation
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from core.smart_chunker import call_smart_chunker, ChunkerError
from core.agents import (
    SectionPlannerAgent,
    NarrationWriterAgent,
    VisualSpecArtistAgent,
    RendererSpecAgent,
    MemoryFlashcardAgent,
    RecapSceneAgent,
    AgentError
)
from core.agents.manim_code_generator import (
    ManimCodeGenerator,
    build_manim_section_data,
    integrate_manim_code_into_section
)
from core.merge_step_v15 import merge_agent_outputs
from core.tts_duration import update_durations_from_tts, update_durations_two_pass, TTSProvider
from core.analytics import AnalyticsTracker, create_tracker
from core.renderer_executor import render_all_topics, enforce_renderer_policy

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "1.5"


def _json_serializer(obj):
    """Custom JSON serializer for non-serializable objects."""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return str(obj)
    return str(obj)


def _save_artifact(output_dir: Optional[Path], filename: str, data: Dict) -> None:
    """Save agent output as artifact for debugging (ISS-149).
    
    Uses safe serialization with fallback to str() for non-serializable objects.
    Failures are logged but do not crash the pipeline.
    """
    if not output_dir:
        return
    
    try:
        artifacts_dir = Path(output_dir) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        artifact_path = artifacts_dir / filename
        with open(artifact_path, "w") as f:
            json.dump(data, f, indent=2, default=_json_serializer)
        logger.debug(f"[Artifacts] Saved {filename}")
    except Exception as e:
        logger.warning(f"[Artifacts] Failed to save {filename}: {e}")


class PipelineError(Exception):
    """Error raised when pipeline fails."""
    def __init__(self, message: str, phase: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.phase = phase
        self.details = details or {}


def _extract_source_content(markdown_content: str, source_blocks: List[int]) -> str:
    """Extract relevant markdown content for a section based on source blocks."""
    lines = markdown_content.split('\n')
    if not source_blocks:
        return markdown_content[:3000]
    
    block_num = 0
    extracted = []
    current_block = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#') or (stripped and not current_block):
            if current_block and block_num in source_blocks:
                extracted.extend(current_block)
            current_block = [line]
            block_num += 1
        else:
            current_block.append(line)
    
    if current_block and block_num in source_blocks:
        extracted.extend(current_block)
    
    return '\n'.join(extracted) if extracted else markdown_content[:3000]


def process_markdown_to_presentation_v15(
    markdown_content: str,
    subject: str,
    grade: str,
    job_id: str,
    update_status_callback=None,
    generate_tts: bool = True,
    output_dir: Optional[Path] = None,
    tts_provider: TTSProvider = "edge_tts",
    dry_run: bool = False,
    skip_wan: bool = False
) -> Tuple[Dict, AnalyticsTracker]:
    """
    V1.5 Pipeline: Process markdown to presentation.json using split agents.
    
    Pipeline Flow:
    1. SmartChunker → topics
    2. SectionPlanner(topics) → section_blueprints[]
    3. FOR EACH blueprint:
       - NarrationWriter(blueprint) → narration
       - VisualSpecArtist(blueprint, narration) → visuals
       - IF renderer != 'none': RendererSpecAgent(visuals) → render_spec
    4. MemoryFlashcardAgent(markdown) → memory_section
    5. RecapSceneAgent(markdown, concepts) → recap_section
    6. MergeStep(all_outputs) → presentation.json
    7. TTS(presentation) → audio files + updated durations
    
    Args:
        markdown_content: Raw markdown content from document
        subject: Subject area (e.g., "Biology", "Physics")
        grade: Grade level (e.g., "Grade 10")
        job_id: Unique job identifier
        update_status_callback: Optional callback for status updates
        generate_tts: Whether to generate TTS audio
        output_dir: Output directory for assets
        tts_provider: TTS provider - "edge_tts" (default), "narakeet", "estimate"
        
    Returns:
        Tuple of (presentation dict, analytics tracker)
        
    Raises:
        PipelineError: If any pipeline phase fails
    """
    logger.info(f"[Pipeline v1.5] Starting for job {job_id}")
    
    tracker = create_tracker(job_id)
    tracker.start_pipeline()
    
    def update_status(phase: str, message: str):
        if update_status_callback:
            update_status_callback(job_id, phase, message)
        logger.info(f"[{phase}] {message}")
    
    def log(msg: str):
        logger.info(msg)
    
    try:
        update_status("chunker", "Analyzing content structure...")
        chunker_output = call_smart_chunker(
            markdown_content=markdown_content,
            subject=subject,
            tracker=tracker,
            max_retries=2
        )
        topics = chunker_output.get("topics", [])
        logger.info(f"[Pipeline v1.5] Extracted {len(topics)} topics")
        
        _save_artifact(output_dir, "01_chunker.json", chunker_output)
        
        quiz_questions = chunker_output.get("quiz_questions", [])
        logger.info(f"[Pipeline v1.5] Extracted {len(quiz_questions)} quiz questions")
        
        update_status("section_planner", "Planning section structure...")
        section_planner = SectionPlannerAgent(tracker=tracker, log_func=log)
        planner_output = section_planner.run(
            topics=topics,
            subject=subject,
            grade=grade,
            quiz_questions=quiz_questions
        )
        blueprints = planner_output.get("sections", [])
        logger.info(f"[Pipeline v1.5] Planned {len(blueprints)} sections")
        
        _save_artifact(output_dir, "02_planner.json", planner_output)
        
        section_artifacts = []
        manim_failed_sections = []
        
        for i, blueprint in enumerate(blueprints):
            section_type = blueprint.get("section_type")
            section_id = blueprint.get("section_id")
            
            if section_type in ["memory", "recap"]:
                continue
            
            update_status("narration", f"Writing narration for {section_id}...")
            
            source_topics = blueprint.get("source_topics", [])
            topic_blocks = []
            for topic in topics:
                if topic.get("topic_id") in source_topics:
                    topic_blocks.extend(topic.get("source_blocks", []))
            source_content = _extract_source_content(markdown_content, topic_blocks)
            
            section_quiz_questions = quiz_questions if section_type == "quiz" else []
            
            narration_writer = NarrationWriterAgent(tracker=tracker, log_func=log)
            narration_output = narration_writer.run(
                section_blueprint=blueprint,
                source_markdown=source_content,
                quiz_questions=section_quiz_questions
            )
            
            update_status("visuals", f"Designing visuals for {section_id}...")
            visual_artist = VisualSpecArtistAgent(tracker=tracker, log_func=log)
            visuals_output = visual_artist.run(
                section_blueprint=blueprint,
                narration=narration_output.get("narration", {}),
                source_markdown=source_content
            )
            
            render_spec = None
            renderer = blueprint.get("suggested_renderer", "none")
            
            if renderer == "video":
                update_status("renderer_spec", f"Creating {renderer} spec for {section_id}...")
                
                visual_beats = visuals_output.get("visual_beats", [])
                narration_summary = narration_output.get("narration", {}).get("full_text", "")[:500]
                
                try:
                    renderer_agent = RendererSpecAgent(
                        renderer_type=renderer,
                        tracker=tracker,
                        log_func=log
                    )
                    render_spec = renderer_agent.run(
                        section_id=section_id,
                        visual_beats=visual_beats,
                        narration_summary=narration_summary,
                        is_recap=False
                    )
                except AgentError as e:
                    logger.warning(f"[Pipeline v1.5] RendererSpec failed for {section_id}: {e}")
                    render_spec = None
            
            artifact = {
                "blueprint": blueprint,
                "narration": narration_output,
                "visuals": visuals_output,
                "render_spec": render_spec
            }
            section_artifacts.append(artifact)
            
            artifact_idx = len(section_artifacts) + 2
            _save_artifact(output_dir, f"{artifact_idx:02d}_{section_id}_narration.json", narration_output)
            _save_artifact(output_dir, f"{artifact_idx:02d}_{section_id}_visuals.json", visuals_output)
            if render_spec:
                _save_artifact(output_dir, f"{artifact_idx:02d}_{section_id}_render_spec.json", render_spec)
        
        update_status("memory", "Creating memory section with narration...")
        
        memory_blueprint = {
            "section_id": "memory",
            "section_type": "memory",
            "title": f"{subject} - Key Flashcards",
            "learning_goals": ["Review key concepts", "Test your understanding"],
            "suggested_renderer": "none",
            "avatar_visibility": "always",
            "avatar_position": "right",
            "avatar_width_percent": 52
        }
        
        memory_narration_writer = NarrationWriterAgent(tracker=tracker, log_func=log)
        memory_narration_output = memory_narration_writer.run(
            section_blueprint=memory_blueprint,
            source_markdown=markdown_content[:2000]
        )
        _save_artifact(output_dir, "memory_narration.json", memory_narration_output)
        
        memory_agent = MemoryFlashcardAgent(tracker=tracker, log_func=log)
        memory_output = memory_agent.run(
            source_markdown=markdown_content,
            subject=subject
        )
        memory_output["narration"] = memory_narration_output.get("narration", {})
        
        _save_artifact(output_dir, "memory.json", memory_output)
        
        key_concepts = [f.get("front", "") for f in memory_output.get("flashcards", [])]
        
        update_status("recap", "Creating recap section with narration...")
        
        recap_blueprint = {
            "section_id": "recap",
            "section_type": "recap",
            "title": f"{subject} - Chapter Recap",
            "learning_goals": ["Review all major concepts", "Reinforce learning with video"],
            "suggested_renderer": "video",
            "avatar_visibility": "always",
            "avatar_position": "right",
            "avatar_width_percent": 52
        }
        
        recap_narration_writer = NarrationWriterAgent(tracker=tracker, log_func=log)
        recap_narration_output = recap_narration_writer.run(
            section_blueprint=recap_blueprint,
            source_markdown=markdown_content[:3000]
        )
        _save_artifact(output_dir, "recap_narration.json", recap_narration_output)
        
        recap_agent = RecapSceneAgent(tracker=tracker, log_func=log)
        recap_output = recap_agent.run(
            source_markdown=markdown_content,
            subject=subject,
            key_concepts=key_concepts
        )
        recap_output["narration"] = recap_narration_output.get("narration", {})
        
        video_prompts = recap_output.get("video_prompts", [])
        for i, vp in enumerate(video_prompts):
            prompt = vp.get("prompt", "") if isinstance(vp, dict) else str(vp)
            char_count = len(prompt)
            word_count = len(prompt.split()) if prompt else 0
            if char_count > 800:
                raise PipelineError(
                    f"Recap prompt {i+1} exceeds 800 char limit ({char_count} chars). "
                    f"LLM must generate within limits.",
                    phase="recap_validation"
                )
            if word_count < 80:
                raise PipelineError(
                    f"Recap prompt {i+1} has only {word_count} words (minimum 80). "
                    f"Preview: '{prompt[:100]}...'",
                    phase="recap_validation"
                )
            logger.info(f"[Pipeline v1.5] Recap prompt {i+1}: {word_count} words, {char_count} chars - VALID")
        
        _save_artifact(output_dir, "recap.json", recap_output)
        
        update_status("merge", "Combining all components...")
        presentation = merge_agent_outputs(
            section_artifacts=section_artifacts,
            memory_output=memory_output,
            recap_output=recap_output,
            subject=subject,
            grade=grade
        )
        
        logger.info(f"[Pipeline v1.5] Merged {len(presentation.get('sections', []))} sections")
        
        if generate_tts:
            update_status("tts_duration", f"ISS-160: Two-pass TTS (pyttsx3 measure -> {tts_provider} audio)...")
            presentation = update_durations_two_pass(
                presentation=presentation,
                output_dir=output_dir,
                production_provider=tts_provider
            )
        
        update_status("manim_code", "Generating Manim code with actual TTS timing...")
        manim_generator = ManimCodeGenerator()
        manim_success_count = 0
        manim_fail_count = 0
        
        for i, section in enumerate(presentation.get("sections", [])):
            renderer = section.get("renderer", "none")
            section_id = section.get("section_id", f"section_{i}")
            
            if renderer == "manim":
                logger.info(f"[Pipeline v1.5] Generating Manim code for {section_id}")
                
                narration = section.get("narration", {})
                segments = narration.get("segments", []) or section.get("segments", [])
                visual_beats = section.get("visual_beats", [])
                segment_enrichments = section.get("segment_enrichments", [])
                
                manim_input = build_manim_section_data(
                    section=section,
                    narration_segments=segments,
                    visual_beats=visual_beats,
                    segment_enrichments=segment_enrichments
                )
                
                try:
                    manim_code, validation_errors = manim_generator.generate(manim_input)
                    
                    if manim_code and len(manim_code) > 50:
                        if validation_errors:
                            logger.warning(f"[Pipeline v1.5] Manim validation warnings for {section_id}: {validation_errors}")
                        
                        section = integrate_manim_code_into_section(section, manim_code)
                        presentation["sections"][i] = section
                        
                        logger.info(f"[Pipeline v1.5] Manim code generated for {section_id} ({len(manim_code)} chars)")
                        manim_success_count += 1
                    else:
                        manim_failed_sections.append({
                            "section_id": section_id,
                            "section_index": i,
                            "error": "Empty or too short code returned",
                            "validation_errors": validation_errors,
                            "manim_input": manim_input
                        })
                        manim_fail_count += 1
                        logger.warning(f"[Pipeline v1.5] Manim code empty/short for {section_id}")
                    
                except Exception as e:
                    manim_failed_sections.append({
                        "section_id": section_id,
                        "section_index": i,
                        "error": str(e),
                        "manim_input": manim_input
                    })
                    manim_fail_count += 1
                    logger.error(f"[Pipeline v1.5] Manim code generation failed for {section_id}: {e}")
        
        if manim_failed_sections:
            _save_artifact(output_dir, "manim_failed_sections.json", {
                "failed_count": len(manim_failed_sections),
                "sections": manim_failed_sections,
                "note": "These sections can be retried via /api/v15/retry-manim endpoint"
            })
            logger.info(f"[Pipeline v1.5] Manim generation: {manim_success_count} success, {manim_fail_count} failed (saved for retry)")
        
        if output_dir and not dry_run:
            update_status("render_execute", "Rendering videos...")
            videos_dir = Path(output_dir) / "videos"
            videos_dir.mkdir(parents=True, exist_ok=True)
            
            presentation = enforce_renderer_policy(presentation)
            
            rendered_videos = render_all_topics(
                presentation=presentation,
                output_dir=str(videos_dir),
                dry_run=dry_run,
                skip_wan=skip_wan,
                output_dir_base=str(output_dir)
            )
            
            for result in rendered_videos:
                section_id_result = result.get("topic_id")
                video_path = result.get("video_path")
                beat_videos = result.get("beat_videos", [])
                recap_video_paths = result.get("recap_video_paths", [])
                
                for section in presentation.get("sections", []):
                    if section.get("section_id") == section_id_result:
                        if video_path:
                            rel_path = Path(video_path).name if "/" in str(video_path) else video_path
                            section["video_path"] = f"videos/{rel_path}"
                        if beat_videos:
                            section["beat_videos"] = [f"videos/{Path(p).name}" for p in beat_videos]
                        if recap_video_paths:
                            section["recap_video_paths"] = [f"videos/{Path(p).name}" for p in recap_video_paths]
                        break
            
            success_count = sum(1 for r in rendered_videos if r.get("status") in ["success", "skipped"])
            fail_count = sum(1 for r in rendered_videos if r.get("status") == "failed")
            logger.info(f"[Pipeline v1.5] Rendering complete: {success_count} success, {fail_count} failed")
        
        tracker.end_pipeline(status="completed")
        logger.info(f"[Pipeline v1.5] Completed successfully for job {job_id}")
        
        return presentation, tracker
        
    except ChunkerError as e:
        tracker.end_pipeline(status="failed", error=str(e))
        raise PipelineError(f"Chunker failed: {e}", phase="chunker")
        
    except AgentError as e:
        tracker.end_pipeline(status="failed", error=str(e))
        raise PipelineError(f"Agent failed: {e}", phase=e.agent_name)
        
    except Exception as e:
        tracker.end_pipeline(status="failed", error=str(e))
        logger.exception(f"[Pipeline v1.5] Unexpected error: {e}")
        raise PipelineError(f"Pipeline error: {e}", phase="unknown")
