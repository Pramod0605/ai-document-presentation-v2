import os
import traceback
from pathlib import Path
from render.wan.wan_runner import render_wan_video
from render.manim.manim_runner import render_manim_video
from core.visual_compiler import compile_section_visuals, VisualCompilationError


MATH_PHYSICS_SUBJECTS = [
    "mathematics", "maths", "math", "algebra", "geometry", "calculus",
    "trigonometry", "statistics", "physics", "mechanics", "electrostatics",
    "electromagnetism", "thermodynamics", "optics", "quantum", "kinematics",
    "chemistry"
]


def enforce_renderer_policy(presentation: dict) -> dict:
    """Enforce renderer selection based on subject and section type.
    
    POLICY:
    - For math/physics subjects: Force Manim for content/example sections
    - Recap sections: Always use WAN (storyboard visualization)
    - Intro/Summary/Memory: Text-only (no video rendering needed)
    
    This overrides the LLM Director's renderer choice to ensure consistency.
    """
    subject = presentation.get("subject", "").lower()
    is_math_physics = any(subj in subject for subj in MATH_PHYSICS_SUBJECTS)
    
    if not is_math_physics:
        return presentation
    
    sections = presentation.get("sections", presentation.get("topics", []))
    changes_made = 0
    
    for section in sections:
        section_type = section.get("section_type", "content")
        current_renderer = section.get("renderer", "wan_video")
        
        if section_type in ("content", "example"):
            if current_renderer != "manim":
                section["renderer"] = "manim"
                section["renderer_override_reason"] = f"Math/physics subject '{subject}' requires Manim for {section_type} sections"
                changes_made += 1
                print(f"[RENDERER POLICY] Section {section.get('id')}: Forced WAN -> Manim (math/physics subject)")
    
    if changes_made > 0:
        print(f"[RENDERER POLICY] Applied {changes_made} renderer overrides for subject: {subject}")
    
    return presentation


def execute_renderer(topic: dict, output_dir: str, dry_run: bool = False, skip_wan: bool = False, trace_output_dir: str = None, strict_mode: bool = True) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    
    topic_id = topic.get("id", 1)
    renderer = topic.get("renderer", "wan_video")
    section_type = topic.get("section_type", "content")
    visual_beats = topic.get("visual_beats", [])
    
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
        "compilation_errors": []
    }
    
    if section_type in ["content", "example"] and visual_beats and strict_mode:
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
        result["video_path"] = video_path
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        print(f"Error rendering topic {topic_id}: {e}")
    
    return result


def render_all_topics(presentation: dict, output_dir: str, dry_run: bool = False, skip_wan: bool = False, output_dir_base: str = None, strict_mode: bool = True) -> list:
    os.makedirs(output_dir, exist_ok=True)
    
    trace_output_dir = output_dir_base or str(Path(output_dir).parent)
    
    rendered_videos = []
    topics = presentation.get("sections", presentation.get("topics", []))
    success_count = 0
    fail_count = 0
    compile_fail_count = 0
    
    mode_label = "[DRY RUN] " if dry_run else ""
    skip_label = "[SKIP WAN] " if skip_wan else ""
    strict_label = "[STRICT] " if strict_mode else ""
    
    for topic in topics:
        topic_id = topic.get("id", 1)
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
        elif result["status"] == "compilation_failed":
            compile_fail_count += 1
            print(f"  -> Compilation Failed: {result['error']}")
        else:
            fail_count += 1
            print(f"  -> Failed: {result['error']}")
    
    print(f"{mode_label}{skip_label}{strict_label}Rendering complete: {success_count} success, {compile_fail_count} compilation failures, {fail_count} render failures")
    return rendered_videos
