import os
import json
import traceback
from pathlib import Path
from render.wan.wan_runner import render_wan_video
from render.manim.manim_runner import render_manim_video
from core.visual_compiler import compile_section_visuals, VisualCompilationError
from core.traceability import log_render_prompt
from core.wan_prompt_validator import validate_video_prompts, log_prompt_quality_summary
from core.dry_run_validator import (
    validate_presentation_dry_run,
    format_validation_report,
    DryRunValidationResult
)


TEXT_ONLY_SECTION_TYPES = ["intro", "summary", "memory", "quiz"]


class DryRunValidationError(Exception):
    """Raised when dry run validation fails."""
    pass


def enforce_renderer_policy(presentation: dict) -> dict:
    """Enforce renderer selection based on section type.
    
    POLICY (as agreed):
    - INTRO/SUMMARY/MEMORY: TEXT-ONLY (no video rendering)
    - CONTENT/EXAMPLE: Use LLM Director's choice (WAN for physics concepts, Manim for math/LaTeX)
    - RECAP: Always WAN (5 storyboard scenes)
    
    This enforces text-only sections but trusts the LLM Director for content/example.
    """
    sections = presentation.get("sections", presentation.get("topics", []))
    changes_made = 0
    
    for section in sections:
        section_type = section.get("section_type", "content")
        current_renderer = section.get("renderer", "wan_video")
        
        if section_type in TEXT_ONLY_SECTION_TYPES:
            if current_renderer and current_renderer != "none":
                section["renderer"] = "none"
                section["renderer_override_reason"] = f"Section type '{section_type}' is text-only (no video rendering)"
                changes_made += 1
                print(f"[RENDERER POLICY] Section {section.get('id')} ({section_type}): Forced to TEXT-ONLY")
        
        elif section_type == "recap":
            if current_renderer != "wan_video" and current_renderer != "wan":
                section["renderer"] = "wan_video"
                section["renderer_override_reason"] = "Recap sections use WAN for storyboard visualization"
                changes_made += 1
                print(f"[RENDERER POLICY] Section {section.get('id')}: Forced to WAN (recap)")
    
    if changes_made > 0:
        print(f"[RENDERER POLICY] Applied {changes_made} renderer overrides")
    
    return presentation


def execute_renderer(topic: dict, output_dir: str, dry_run: bool = False, skip_wan: bool = False, trace_output_dir: str = "", strict_mode: bool = True) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    
    topic_id = topic.get("section_id", topic.get("id", 1))
    renderer = topic.get("renderer", "wan_video")
    section_type = topic.get("section_type", "content")
    visual_beats = topic.get("visual_beats", [])
    
    manim_scene_spec = topic.get("manim_scene_spec") or topic.get("render_spec", {}).get("manim_scene_spec")
    video_prompts = topic.get("video_prompts") or topic.get("render_spec", {}).get("video_prompts")
    has_v12_specs = bool(manim_scene_spec or video_prompts)
    
    if renderer == "none" or section_type in TEXT_ONLY_SECTION_TYPES:
        return {
            "topic_id": topic_id,
            "section_type": section_type,
            "renderer": "none",
            "status": "skipped",
            "video_path": None,
            "reason": f"Section type '{section_type}' is text-only (no video rendering)"
        }
    
    if visual_beats:
        if "explanation_plan" not in topic:
            topic["explanation_plan"] = {}
        topic["explanation_plan"]["visual_beats"] = visual_beats
    
    result = {
        "topic_id": topic_id,
        "section_type": section_type,
        "renderer": renderer,
        "status": "pending",
        "video_path": None,
        "error": None,
        "visual_beats_used": len(visual_beats) if visual_beats else 0,
        "dry_run": dry_run,
        "compilation_errors": [],
        "v12_specs_used": has_v12_specs
    }
    
    if has_v12_specs:
        print(f"[v1.2 MODE] Section {topic_id} has pre-compiled renderer specs - bypassing Visual Compiler")
        if "explanation_plan" not in topic:
            topic["explanation_plan"] = {}
        
        if manim_scene_spec and renderer == "manim":
            if manim_scene_spec.get("manim_code"):
                topic["explanation_plan"]["v15_manim_code"] = manim_scene_spec.get("manim_code")
                print(f"  [OK] Using v1.5 manim_code: {len(manim_scene_spec.get('manim_code', ''))} chars")
                log_render_prompt(topic_id, 0, "manim", manim_scene_spec.get("manim_code", "")[:500])
            else:
                topic["explanation_plan"]["v12_manim_scene_spec"] = manim_scene_spec
                print(f"  [OK] Using v1.2 manim_scene_spec: {len(manim_scene_spec.get('objects', []))} objects, {len(manim_scene_spec.get('animation_sequence', []))} animations")
                log_render_prompt(topic_id, 0, "manim", json.dumps(manim_scene_spec, indent=2))
        elif video_prompts:
            if isinstance(video_prompts, list):
                combined_prompts = "\n\n".join([
                    f"[Beat {p.get('beat_id', i)}]: {p.get('prompt', '')}" 
                    for i, p in enumerate(video_prompts)
                ])
                topic["explanation_plan"]["compiled_wan_prompt"] = combined_prompts
                topic["explanation_plan"]["video_prompts"] = video_prompts
                print(f"  [OK] Using v1.2 video_prompts: {len(video_prompts)} beat prompts")
                for i, p in enumerate(video_prompts):
                    log_render_prompt(topic_id, i, "video", p.get("prompt", ""))
                
                quality_summary = log_prompt_quality_summary(video_prompts, topic_id)
                if quality_summary["issues"]:
                    print(f"  [QUALITY] Avg score: {quality_summary['avg_quality']}, Issues: {len(quality_summary['issues'])}")
                    for issue in quality_summary["issues"][:3]:
                        print(f"    - {issue}")
            elif isinstance(video_prompts, dict):
                prompt_text = video_prompts.get("prompt", "")
                topic["explanation_plan"]["compiled_wan_prompt"] = prompt_text
                print(f"  [OK] Using v1.2 video_prompts: {len(prompt_text)} chars")
                log_render_prompt(topic_id, 0, "video", prompt_text)
            else:
                topic["explanation_plan"]["compiled_wan_prompt"] = str(video_prompts)
                print(f"  [OK] Using v1.2 video_prompts: {len(str(video_prompts))} chars")
                log_render_prompt(topic_id, 0, "video", str(video_prompts))
    
    elif section_type in ["content", "example"] and visual_beats and strict_mode:
        print(f"[VISUAL COMPILER] Compiling {len(visual_beats)} visual beats for section {topic_id}")
        
        wan_prompt, manim_plan, compilation_errors = compile_section_visuals(topic)
        
        if compilation_errors:
            error_messages = [str(e) for e in compilation_errors]
            result["status"] = "compilation_failed"
            result["error"] = f"Visual compilation failed: {len(compilation_errors)} errors"
            result["compilation_errors"] = error_messages
            
            for err in compilation_errors:
                print(f"  [FAIL] {err}")
            
            return result
        
        if renderer == "manim" and manim_plan:
            topic["explanation_plan"]["compiled_manim_plan"] = manim_plan
            print(f"  [OK] Compiled Manim plan: {manim_plan.get('scene_type', 'unknown')}")
        elif wan_prompt:
            topic["explanation_plan"]["compiled_wan_prompt"] = wan_prompt
            print(f"  [OK] Compiled WAN prompt: {len(wan_prompt)} chars")
    
    try:
        if renderer == "manim":
            video_path = render_manim_video(topic, output_dir, dry_run=dry_run, trace_output_dir=trace_output_dir)
        else:
            video_path = render_wan_video(topic, output_dir, dry_run=dry_run, skip_wan=skip_wan, trace_output_dir=trace_output_dir)
        
        result["status"] = "success"
        
        # ISS-093 FIX: Handle Manim multi-beat returns (list of paths)
        if isinstance(video_path, list):
            result["video_path"] = video_path[0] if video_path else None
            result["beat_videos"] = video_path
            print(f"[RENDER] Manim multi-beat: {len(video_path)} beat videos for section {topic_id}")
        else:
            result["video_path"] = video_path
        
        # ISS-092 FIX: Capture recap video paths if they were set by WAN renderer
        if topic.get("_recap_video_paths"):
            result["recap_video_paths"] = topic["_recap_video_paths"]
            print(f"[RENDER] Captured {len(result['recap_video_paths'])} recap video paths for section {topic_id}")
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        print(f"Error rendering topic {topic_id}: {e}")
    
    return result


def validate_before_render(presentation: dict, output_dir: str, strict_v13: bool = True) -> DryRunValidationResult:
    """
    ISS-078 FIX: Run comprehensive validation before rendering.
    
    This validates all render specs are complete:
    - WAN prompts have 300+ words (v1.3)
    - Manim scene specs are complete
    - Display directives are present
    - Renderer-subject matches are valid
    
    Args:
        presentation: The presentation dict
        output_dir: Output directory for videos
        strict_v13: Enforce v1.3 requirements
    
    Returns:
        DryRunValidationResult with all errors and warnings
    """
    result = validate_presentation_dry_run(presentation, output_dir, strict_v13=strict_v13)
    
    report = format_validation_report(result)
    print(report)
    
    report_path = Path(output_dir).parent / "dry_run_validation.txt"
    try:
        with open(report_path, "w") as f:
            f.write(report)
        print(f"[DRY RUN] Validation report saved to: {report_path}")
    except Exception as e:
        print(f"[DRY RUN] Could not save report: {e}")
    
    return result


def render_all_topics(presentation: dict, output_dir: str, dry_run: bool = False, skip_wan: bool = False, output_dir_base: str = "", strict_mode: bool = True) -> list:
    os.makedirs(output_dir, exist_ok=True)
    
    trace_output_dir = output_dir_base or str(Path(output_dir).parent)
    
    if dry_run:
        print("[DRY RUN] Running comprehensive validation before render simulation...")
        validation_result = validate_before_render(
            presentation, 
            output_dir, 
            strict_v13=strict_mode
        )
        
        if not validation_result.is_valid:
            print(f"[DRY RUN] VALIDATION FAILED with {len(validation_result.errors)} errors")
            for err in validation_result.errors[:10]:
                print(f"  {err}")
            raise DryRunValidationError(
                f"Dry run validation failed: {len(validation_result.errors)} errors. "
                f"Fix these issues before production run. See dry_run_validation.txt for details."
            )
        else:
            print(f"[DRY RUN] Validation PASSED ({len(validation_result.warnings)} warnings)")
    
    rendered_videos = []
    topics = presentation.get("sections", presentation.get("topics", []))
    success_count = 0
    fail_count = 0
    compile_fail_count = 0
    
    mode_label = "[DRY RUN] " if dry_run else ""
    skip_label = "[SKIP WAN] " if skip_wan else ""
    strict_label = "[STRICT] " if strict_mode else ""
    
    for topic in topics:
        topic_id = topic.get("section_id", topic.get("id", 1))
        print(f"{mode_label}{skip_label}{strict_label}Rendering topic {topic_id}: {topic.get('title', 'Untitled')}")
        
        result = execute_renderer(
            topic, output_dir, 
            dry_run=dry_run, 
            skip_wan=skip_wan, 
            trace_output_dir=trace_output_dir,
            strict_mode=strict_mode
        )
        rendered_videos.append(result)
        
        if result["status"] == "success":
            success_count += 1
            print(f"  -> Success: {result['video_path']}")
        elif result["status"] == "skipped":
            success_count += 1
            print(f"  -> Skipped (text-only): {result.get('reason', 'No video needed')}")
        elif result["status"] == "compilation_failed":
            compile_fail_count += 1
            print(f"  -> Compilation Failed: {result['error']}")
        else:
            fail_count += 1
            print(f"  -> Failed: {result.get('error', 'Unknown error')}")
    
    print(f"{mode_label}{skip_label}{strict_label}Rendering complete: {success_count} success, {compile_fail_count} compilation failures, {fail_count} render failures")
    return rendered_videos
