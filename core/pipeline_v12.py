"""
Pipeline v1.2 - 3-Phase LLM Architecture (Parse → Direct → Render)

This pipeline uses the v1.2 architecture with clear separation of concerns:
- Parse: Chunker (Gemini Flash) - Split markdown into chunks
- Direct: Director (Gemini Pro) - Pedagogy, structure, timing (NO renderer code)
- Render: Specialized Renderers - Generate scene specs
    - Manim Renderer (Claude Sonnet) - Math/physics
    - Remotion Renderer (Claude Sonnet) - Motion graphics (when enabled)
    - Video Renderer (Gemini Pro) - WAN video prompts

When use_remotion=False (default), Remotion content routes to Video (WAN) instead.

For v1.1 pipeline, see pipeline_v11.py (backup).
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from core.datalab_client import pdf_to_markdown
from core.llm_client_v12 import generate_presentation_v12, PipelineError
from core.renderer_executor import render_all_topics, enforce_renderer_policy
from core.image_processor import extract_images_from_markdown, strip_base64_from_markdown, create_image_list_for_llm
from core.hard_fail_validator import validate_presentation_hard_fails, format_hard_fail_report
from core.traceability import init_traceability, log_event, log_validation, log_hard_fail, complete_trace, save_render_prompts_json
from core.schema_validator import validate_presentation as validate_schema, format_errors_for_retry
from tts.generate_audio import generate_all_audio
from render.render_trace import clear_render_trace


def normalize_director_output(presentation: dict) -> dict:
    """
    Normalize Director LLM output to canonical v1.3 schema.
    
    Converts various LLM output field names to canonical schema:
    - narration_beats → narration_segments + section.narration
    - narration_and_visuals → narration_segments + section.narration
    - narration (when list) → narration_segments + section.narration (string)
    - recap.scenes → recap.recap_scenes
    - Ensures visual_beats array is populated from embedded visual_beat objects
    
    This allows the hard_fail_validator to work correctly regardless of 
    minor LLM output variations.
    """
    sections = presentation.get("sections", [])
    
    for section in sections:
        section_type = section.get("section_type", "")
        
        if "scenes" in section and section_type == "recap":
            scenes = section.pop("scenes", [])
            recap_scenes = []
            for i, scene in enumerate(scenes):
                scene_narration = scene.get("narration", scene.get("narration_script", ""))
                recap_scene = {
                    "scene": i + 1,
                    "concept_title": scene.get("scene_title", scene.get("concept_title", f"Scene {i+1}")),
                    "narration": scene_narration,
                    "word_count": scene.get("word_count", len(scene_narration.split()) if scene_narration else 0),
                    "duration_seconds": scene.get("duration_seconds", 20)
                }
                if "visual_beat" in scene:
                    vb = scene["visual_beat"]
                    recap_scene["video_prompt"] = vb.get("video_spec", {}).get("scene_description", "")
                    recap_scene["renderer"] = vb.get("renderer", "video")
                recap_scenes.append(recap_scene)
            section["recap_scenes"] = recap_scenes
            print(f"[Normalize] Converted {len(recap_scenes)} scenes → recap_scenes for recap section")
        
        existing_narration = section.get("narration")
        if isinstance(existing_narration, list):
            source_array = existing_narration
            source_field = "narration (list)"
        else:
            source_array = section.get("narration_and_visuals") or section.get("narration_beats") or []
            source_field = "narration_and_visuals" if "narration_and_visuals" in section else "narration_beats" if "narration_beats" in section else None
        
        if source_array and "narration_segments" not in section:
            narration_segments = []
            visual_beats = []
            full_narration_parts = []
            
            for i, nav in enumerate(source_array):
                narration_text = nav.get("narration") or nav.get("narration_script") or nav.get("text") or ""
                segment = {
                    "id": nav.get("segment_id", i),
                    "text": narration_text,
                    "duration_seconds": nav.get("duration_seconds", 5)
                }
                
                if "display_directives" in nav:
                    dd = nav["display_directives"]
                    normalized_dd = {}
                    for layer in ["text_layer", "visual_layer", "avatar_layer"]:
                        if layer in dd:
                            layer_val = dd[layer]
                            if isinstance(layer_val, dict):
                                normalized_dd[layer] = layer_val.get("action", "hide")
                            else:
                                normalized_dd[layer] = layer_val
                    segment["display_directives"] = normalized_dd
                
                if "word_count" in nav:
                    segment["word_count"] = nav["word_count"]
                else:
                    segment["word_count"] = len(narration_text.split()) if narration_text else 0
                
                narration_segments.append(segment)
                if narration_text:
                    full_narration_parts.append(narration_text)
                
                if "visual_beat" in nav:
                    vb = nav["visual_beat"]
                    vb["segment_index"] = i
                    visual_beats.append(vb)
            
            section["narration_segments"] = narration_segments
            section["narration"] = " ".join(full_narration_parts)
            
            if visual_beats and not section.get("visual_beats"):
                section["visual_beats"] = visual_beats
            
            if section_type == "recap" and not section.get("recap_scenes"):
                recap_scenes = []
                for i, seg in enumerate(narration_segments):
                    scene = {
                        "scene": i + 1,
                        "concept_title": f"Recap Scene {i + 1}",
                        "narration": seg.get("text", ""),
                        "word_count": seg.get("word_count", 0),
                        "duration_seconds": seg.get("duration_seconds", 20)
                    }
                    if i < len(visual_beats):
                        vb = visual_beats[i]
                        video_spec = vb.get("video_spec", vb.get("manim_scene_spec", {}))
                        scene["video_prompt"] = video_spec.get("scene_description", video_spec.get("description", ""))
                        scene["renderer"] = vb.get("renderer", "video")
                    recap_scenes.append(scene)
                section["recap_scenes"] = recap_scenes
                print(f"[Normalize] Created {len(recap_scenes)} recap_scenes from narration_segments for recap section")
            
            print(f"[Normalize] Converted {len(source_array)} {source_field} → narration_segments for {section_type}")
        
        if section_type == "memory":
            source = section.get("narration_and_visuals") or section.get("narration_beats") or []
            if isinstance(section.get("narration"), list):
                source = section.get("narration")
            if source and len(source) > 0:
                first_nav = source[0]
                if "content" in first_nav:
                    content = first_nav["content"]
                    if "flashcards" in content and "flashcards" not in section:
                        section["flashcards"] = content["flashcards"]
                        print(f"[Normalize] Extracted {len(section['flashcards'])} flashcards for memory section")
    
    return presentation

PLAYER_ASSETS_DIR = Path(__file__).parent.parent / "player" / "assets"


def _reconcile_video_paths(presentation: dict, rendered_videos: list):
    """Update presentation sections with their rendered video paths.
    
    Matches rendered_videos results back to sections using section_id/topic_id.
    """
    sections = presentation.get("sections", presentation.get("topics", []))
    
    video_map = {}
    for result in rendered_videos:
        topic_id = result.get("topic_id")
        if topic_id and result.get("video_path"):
            video_map[str(topic_id)] = result.get("video_path")
    
    for section in sections:
        section_id = section.get("section_id", section.get("id"))
        if section_id and str(section_id) in video_map:
            video_path = video_map[str(section_id)]
            video_filename = Path(video_path).name if video_path else None
            if video_filename:
                section["content_video_path"] = f"videos/{video_filename}"
                section["has_content_video"] = True
    
    print(f"[RECONCILE] Updated {len(video_map)} sections with video paths")


def process_pdf_to_videos_v12(
    pdf_path: str,
    subject: str = "General Science",
    grade: str = "9",
    output_dir: str = None,
    job_id: str = None,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    source_file: str = None,
    use_remotion: bool = False
) -> dict:
    """Process PDF through v1.2 3-phase pipeline (Parse → Direct → Render).
    
    Args:
        use_remotion: If False (default), Remotion content routes to Video (WAN).
    """
    from core.job_manager import job_manager
    
    output_dir = output_dir or str(PLAYER_ASSETS_DIR)
    videos_dir = Path(output_dir) / "videos"
    audio_dir = Path(output_dir) / "audio"
    images_dir = Path(output_dir) / "images"
    
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    
    trace_logger = init_traceability(job_id or "pdf_job_v12", output_dir)
    log_event("pipeline_start", {
        "pipeline_version": "1.2",
        "pipeline_type": "pdf",
        "source_file": source_file,
        "subject": subject,
        "grade": grade,
        "dry_run": dry_run,
        "skip_wan": skip_wan
    })
    
    clear_render_trace(output_dir)
    
    job_status = {
        "status": "processing",
        "pipeline_version": "1.2",
        "started_at": datetime.now().isoformat(),
        "source_file": source_file,
        "steps": []
    }
    
    try:
        if job_id:
            job_manager.set_step(job_id, "Converting PDF to text...", 0)
        
        job_status["steps"].append({"step": "pdf_to_markdown", "status": "started"})
        markdown_content = pdf_to_markdown(pdf_path)
        job_status["steps"][-1]["status"] = "completed"
        
        images_mapping = {}
        images_list_text = ""
        try:
            images_mapping = extract_images_from_markdown(markdown_content, str(images_dir))
            images_list_text = create_image_list_for_llm(images_mapping)
            markdown_for_llm = strip_base64_from_markdown(markdown_content)
            job_status["steps"].append({"step": "extract_images", "status": "completed", "count": len(images_mapping)})
        except Exception as e:
            print(f"[Pipeline v1.2] Image extraction failed: {e}")
            markdown_for_llm = markdown_content
            job_status["steps"].append({"step": "extract_images", "status": "failed", "error": str(e)})
        
        if job_id:
            job_manager.complete_step(job_id, 0)
            job_manager.set_step(job_id, "LLM generating presentation (3-pass v1.2)...", 1)
        
        job_status["steps"].append({"step": "generate_presentation_v12", "status": "started"})
        
        llm_content = markdown_for_llm
        if images_list_text:
            llm_content = f"{images_list_text}\n\n---\n\n{markdown_for_llm}"
        
        presentation, analytics_tracker = generate_presentation_v12(
            markdown_content=llm_content,
            subject=subject,
            grade=grade,
            use_remotion=use_remotion
        )
        
        if presentation and images_mapping:
            presentation["images_mapping"] = {k: v for k, v in images_mapping.items()}
        
        presentation["use_remotion"] = use_remotion
        job_status["steps"][-1]["status"] = "completed"
        job_status["steps"][-1]["analytics"] = analytics_tracker.get_summary()
        
        if presentation:
            print("[Pipeline v1.2 PDF] Normalizing Director output to v1.3 schema...")
            presentation = normalize_director_output(presentation)
        
        presentation_path = Path(output_dir) / "presentation.json"
        if presentation:
            presentation["source_file"] = source_file
            with open(presentation_path, "w") as f:
                json.dump(presentation, f, indent=2)
        
        analytics_path = Path(output_dir) / "analytics.json"
        analytics_tracker.save_to_file(str(analytics_path))
        
        if presentation:
            print("[Pipeline v1.3] Running JSON Schema validation FIRST...")
            schema_valid, schema_errors = validate_schema(presentation)
            if not schema_valid:
                log_validation("schema_validation", None, False, schema_errors[:10], [])
                job_status["steps"].append({
                    "step": "schema_validation",
                    "status": "failed",
                    "errors": schema_errors[:20]
                })
                complete_trace("schema_fail")
                raise PipelineError(
                    f"SCHEMA FAIL: {len(schema_errors)} schema violations. No fallbacks allowed.",
                    "schema_validation",
                    {"schema_errors": schema_errors}
                )
            else:
                log_validation("schema_validation", None, True, [], [])
                job_status["steps"].append({"step": "schema_validation", "status": "passed"})
                print("[Pipeline v1.3] Schema validation PASSED")
            
            print("[Pipeline v1.3] Running Python semantic validation...")
            is_valid, hard_fails = validate_presentation_hard_fails(presentation)
            if not is_valid:
                for hf in hard_fails:
                    log_hard_fail(hf.condition, hf.section_id, hf.details)
                    log_validation("hard_fail_check", hf.section_id, False, [str(hf)], [])
                report = format_hard_fail_report(hard_fails)
                print(report)
                job_status["steps"].append({
                    "step": "hard_fail_validation",
                    "status": "failed",
                    "errors": [str(hf) for hf in hard_fails]
                })
                complete_trace("hard_fail")
                raise PipelineError(
                    f"HARD FAIL: {len(hard_fails)} validation failures",
                    "validation",
                    {"hard_fails": [str(hf) for hf in hard_fails]}
                )
            else:
                log_validation("hard_fail_check", None, True, [], [])
                job_status["steps"].append({"step": "hard_fail_validation", "status": "passed"})
                print("[Pipeline v1.3] Semantic validation PASSED")
        
        if job_id:
            job_manager.complete_step(job_id, 1)
            job_manager.set_step(job_id, "Rendering videos with AI...", 2)
        
        log_event("render_start", {"dry_run": dry_run, "skip_wan": skip_wan})
        
        if presentation:
            presentation["skip_avatar"] = skip_avatar
            presentation = enforce_renderer_policy(presentation)
        
        job_status["steps"].append({"step": "render_videos", "status": "started"})
        rendered_videos = render_all_topics(presentation, str(videos_dir), dry_run=dry_run, skip_wan=skip_wan, output_dir_base=output_dir)
        
        _reconcile_video_paths(presentation, rendered_videos)
        
        with open(presentation_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        success_count = sum(1 for v in rendered_videos if v.get("status") in ("success", "skipped"))
        fail_count = sum(1 for v in rendered_videos if v.get("status") not in ("success", "skipped"))
        
        job_status["steps"][-1]["status"] = "completed" if fail_count == 0 else "partial"
        job_status["steps"][-1]["videos"] = rendered_videos
        job_status["steps"][-1]["success_count"] = success_count
        job_status["steps"][-1]["fail_count"] = fail_count
        job_status["steps"][-1]["dry_run"] = dry_run
        
        if job_id:
            job_manager.complete_step(job_id, 2)
        
        if dry_run:
            job_status["steps"].append({"step": "generate_audio", "status": "skipped", "reason": "dry_run"})
            audio_files = []
        else:
            if job_id:
                job_manager.set_step(job_id, "Generating audio narration...", 3)
            job_status["steps"].append({"step": "generate_audio", "status": "started"})
            audio_files = generate_all_audio(presentation, str(audio_dir))
            job_status["steps"][-1]["status"] = "completed"
            job_status["steps"][-1]["audio_files"] = audio_files
            if job_id:
                job_manager.complete_step(job_id, 3)
        
        job_status["status"] = "completed"
        job_status["completed_at"] = datetime.now().isoformat()
        job_status["presentation_path"] = str(presentation_path)
        job_status["analytics_path"] = str(analytics_path)
        job_status["sections_count"] = len(presentation.get("sections", []))
        job_status["total_cost_usd"] = analytics_tracker.analytics.total_cost_usd
        job_status["dry_run"] = dry_run
        
        save_render_prompts_json()
        complete_trace("completed")
        log_event("pipeline_complete", {"status": "success", "pipeline_version": "1.2"})
        
    except Exception as e:
        job_status["status"] = "failed"
        job_status["error"] = str(e)
        job_status["failed_at"] = datetime.now().isoformat()
        complete_trace("failed")
        raise
    
    return job_status


def process_markdown_to_videos_v12(
    markdown_content: str,
    subject: str = "General Science",
    grade: str = "9",
    output_dir: str = None,
    job_id: str = None,
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    source_file: str = None,
    use_remotion: bool = False
) -> dict:
    """Process Markdown through v1.2 3-phase pipeline (Parse → Direct → Render).
    
    Args:
        use_remotion: If False (default), Remotion content routes to Video (WAN).
    """
    from core.job_manager import job_manager
    
    output_dir = output_dir or str(PLAYER_ASSETS_DIR)
    videos_dir = Path(output_dir) / "videos"
    audio_dir = Path(output_dir) / "audio"
    images_dir = Path(output_dir) / "images"
    
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    
    trace_logger = init_traceability(job_id or "md_job_v12", output_dir)
    log_event("pipeline_start", {
        "pipeline_version": "1.2",
        "pipeline_type": "markdown",
        "source_file": source_file,
        "subject": subject,
        "grade": grade,
        "dry_run": dry_run,
        "skip_wan": skip_wan
    })
    
    clear_render_trace(output_dir)
    
    job_status = {
        "status": "processing",
        "pipeline_version": "1.2",
        "started_at": datetime.now().isoformat(),
        "source_file": source_file,
        "steps": []
    }
    
    try:
        images_mapping = {}
        images_list_text = ""
        try:
            images_mapping = extract_images_from_markdown(markdown_content, str(images_dir))
            images_list_text = create_image_list_for_llm(images_mapping)
            markdown_for_llm = strip_base64_from_markdown(markdown_content)
            job_status["steps"].append({"step": "extract_images", "status": "completed", "count": len(images_mapping)})
        except Exception as e:
            print(f"[Pipeline v1.2] Image extraction failed: {e}")
            markdown_for_llm = markdown_content
            job_status["steps"].append({"step": "extract_images", "status": "failed", "error": str(e)})
        
        if job_id:
            job_manager.set_step(job_id, "LLM generating presentation (3-pass v1.2)...", 0)
        
        job_status["steps"].append({"step": "generate_presentation_v12", "status": "started"})
        
        llm_content = markdown_for_llm
        if images_list_text:
            llm_content = f"{images_list_text}\n\n---\n\n{markdown_for_llm}"
        
        presentation, analytics_tracker = generate_presentation_v12(
            markdown_content=llm_content,
            subject=subject,
            grade=grade,
            use_remotion=use_remotion
        )
        
        if presentation and images_mapping:
            presentation["images_mapping"] = {k: v for k, v in images_mapping.items()}
        
        presentation["use_remotion"] = use_remotion
        job_status["steps"][-1]["status"] = "completed"
        job_status["steps"][-1]["analytics"] = analytics_tracker.get_summary()
        
        if presentation:
            print("[Pipeline v1.2 MD] Normalizing Director output to v1.3 schema...")
            presentation = normalize_director_output(presentation)
        
        presentation_path = Path(output_dir) / "presentation.json"
        if presentation:
            presentation["source_file"] = source_file
            with open(presentation_path, "w") as f:
                json.dump(presentation, f, indent=2)
        
        analytics_path = Path(output_dir) / "analytics.json"
        analytics_tracker.save_to_file(str(analytics_path))
        
        if presentation:
            print("[Pipeline v1.3] Running JSON Schema validation FIRST...")
            schema_valid, schema_errors = validate_schema(presentation)
            if not schema_valid:
                log_validation("schema_validation", None, False, schema_errors[:10], [])
                job_status["steps"].append({
                    "step": "schema_validation",
                    "status": "failed",
                    "errors": schema_errors[:20]
                })
                complete_trace("schema_fail")
                raise PipelineError(
                    f"SCHEMA FAIL: {len(schema_errors)} schema violations. No fallbacks allowed.",
                    "schema_validation",
                    {"schema_errors": schema_errors}
                )
            else:
                log_validation("schema_validation", None, True, [], [])
                job_status["steps"].append({"step": "schema_validation", "status": "passed"})
                print("[Pipeline v1.3] Schema validation PASSED")
            
            print("[Pipeline v1.3] Running Python semantic validation...")
            is_valid, hard_fails = validate_presentation_hard_fails(presentation)
            if not is_valid:
                for hf in hard_fails:
                    log_hard_fail(hf.condition, hf.section_id, hf.details)
                    log_validation("hard_fail_check", hf.section_id, False, [str(hf)], [])
                report = format_hard_fail_report(hard_fails)
                print(report)
                job_status["steps"].append({
                    "step": "hard_fail_validation",
                    "status": "failed",
                    "errors": [str(hf) for hf in hard_fails]
                })
                complete_trace("hard_fail")
                raise PipelineError(
                    f"HARD FAIL: {len(hard_fails)} validation failures",
                    "validation",
                    {"hard_fails": [str(hf) for hf in hard_fails]}
                )
            else:
                log_validation("hard_fail_check", None, True, [], [])
                job_status["steps"].append({"step": "hard_fail_validation", "status": "passed"})
                print("[Pipeline v1.3] Semantic validation PASSED")
        
        if job_id:
            job_manager.complete_step(job_id, 0)
            job_manager.set_step(job_id, "Rendering videos with AI...", 1)
        
        log_event("render_start", {"dry_run": dry_run, "skip_wan": skip_wan})
        
        if presentation:
            presentation["skip_avatar"] = skip_avatar
            presentation = enforce_renderer_policy(presentation)
        
        job_status["steps"].append({"step": "render_videos", "status": "started"})
        rendered_videos = render_all_topics(presentation, str(videos_dir), dry_run=dry_run, skip_wan=skip_wan, output_dir_base=output_dir)
        
        _reconcile_video_paths(presentation, rendered_videos)
        
        with open(presentation_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        success_count = sum(1 for v in rendered_videos if v.get("status") in ("success", "skipped"))
        fail_count = sum(1 for v in rendered_videos if v.get("status") not in ("success", "skipped"))
        
        job_status["steps"][-1]["status"] = "completed" if fail_count == 0 else "partial"
        job_status["steps"][-1]["videos"] = rendered_videos
        job_status["steps"][-1]["success_count"] = success_count
        job_status["steps"][-1]["fail_count"] = fail_count
        job_status["steps"][-1]["dry_run"] = dry_run
        
        if job_id:
            job_manager.complete_step(job_id, 1)
        
        if dry_run:
            job_status["steps"].append({"step": "generate_audio", "status": "skipped", "reason": "dry_run"})
            audio_files = []
        else:
            if job_id:
                job_manager.set_step(job_id, "Generating audio narration...", 2)
            job_status["steps"].append({"step": "generate_audio", "status": "started"})
            audio_files = generate_all_audio(presentation, str(audio_dir))
            job_status["steps"][-1]["status"] = "completed"
            job_status["steps"][-1]["audio_files"] = audio_files
            if job_id:
                job_manager.complete_step(job_id, 2)
        
        job_status["status"] = "completed"
        job_status["completed_at"] = datetime.now().isoformat()
        job_status["presentation_path"] = str(presentation_path)
        job_status["analytics_path"] = str(analytics_path)
        job_status["sections_count"] = len(presentation.get("sections", []))
        job_status["total_cost_usd"] = analytics_tracker.analytics.total_cost_usd
        job_status["dry_run"] = dry_run
        
        save_render_prompts_json()
        complete_trace("completed")
        log_event("pipeline_complete", {"status": "success", "pipeline_version": "1.2"})
        
    except Exception as e:
        job_status["status"] = "failed"
        job_status["error"] = str(e)
        job_status["failed_at"] = datetime.now().isoformat()
        complete_trace("failed")
        raise
    
    return job_status
