#!/usr/bin/env python3
"""
Re-run Manim Renderer LLM to generate new scene specs with updated prompts.
Then re-render the videos.

Usage: python tools/rerender_manim_sections.py <job_id>
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm_client_v12 import pass2_manim_renderer
from core.analytics import AnalyticsTracker
from render.manim.manim_runner import render_manim_video, ManimRenderError


def rerender_manim_sections(job_id: str, dry_run: bool = False):
    """Re-run Manim LLM and render new videos for all Manim sections."""
    job_dir = Path(f"player/jobs/{job_id}")
    presentation_path = job_dir / "presentation.json"
    videos_dir = job_dir / "videos"
    llm_responses_dir = job_dir / "llm_responses"
    
    if not presentation_path.exists():
        print(f"Error: No presentation.json for job {job_id}")
        return
    
    os.environ["CURRENT_JOB_DIR"] = str(job_dir)
    
    with open(presentation_path) as f:
        presentation = json.load(f)
    
    sections = presentation.get("sections", [])
    manim_sections = [s for s in sections if s.get("renderer") == "manim"]
    
    if not manim_sections:
        print(f"No Manim sections found in job {job_id}")
        return
    
    print(f"Found {len(manim_sections)} Manim sections to re-render")
    
    videos_dir.mkdir(exist_ok=True)
    llm_responses_dir.mkdir(exist_ok=True)
    
    tracker = AnalyticsTracker(job_id)
    
    rendered = []
    failed = []
    
    for section in manim_sections:
        section_id = section.get("section_id", "unknown")
        print(f"\n{'='*60}")
        print(f"Processing section: {section_id}")
        print(f"Title: {section.get('section_title', 'Untitled')}")
        
        try:
            print(f"  [1/2] Calling Manim Renderer LLM...")
            result = pass2_manim_renderer(section, tracker)
            
            manim_scene_spec = result.get("manim_scene_spec")
            if not manim_scene_spec:
                print(f"  ERROR: No manim_scene_spec returned")
                failed.append((section_id, "No manim_scene_spec"))
                continue
            
            objects = manim_scene_spec.get("objects", [])
            animations = manim_scene_spec.get("animation_sequence", [])
            print(f"  Got new spec: {len(objects)} objects, {len(animations)} animations")
            
            first_action = animations[0] if animations else {}
            print(f"  First animation: {first_action.get('action', '?')} (duration={first_action.get('duration', '?')})")
            
            total_duration = sum(a.get("duration", 1) for a in animations)
            
            topic = {
                "section_id": section_id,
                "title": section.get("section_title", f"Section {section_id}"),
                "section_type": section.get("section_type", "content"),
                "duration": max(total_duration, 10),
                "explanation_plan": {
                    "v12_manim_scene_spec": manim_scene_spec
                }
            }
            
            print(f"  [2/2] Rendering Manim video...")
            video_path = render_manim_video(
                topic=topic,
                output_dir=str(videos_dir),
                dry_run=dry_run,
                trace_output_dir=str(job_dir)
            )
            
            print(f"  SUCCESS: {video_path}")
            rendered.append((section_id, video_path))
            
            for i, s in enumerate(sections):
                if s.get("section_id") == section_id:
                    sections[i]["content_video_path"] = str(Path(video_path).name)
                    sections[i]["manim_scene_spec"] = manim_scene_spec
                    break
            
        except Exception as e:
            print(f"  ERROR: {e}")
            failed.append((section_id, str(e)))
    
    presentation["sections"] = sections
    with open(presentation_path, "w") as f:
        json.dump(presentation, f, indent=2)
    print(f"\nUpdated presentation.json with new video paths and scene specs")
    
    analytics_path = job_dir / "analytics_rerender.json"
    with open(analytics_path, "w") as f:
        json.dump(tracker.get_summary(), f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Rendered: {len(rendered)}")
    for section_id, path in rendered:
        print(f"  - {section_id}: {path}")
    
    if failed:
        print(f"\nFailed: {len(failed)}")
        for section_id, reason in failed:
            print(f"  - {section_id}: {reason}")
    
    return rendered, failed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/rerender_manim_sections.py <job_id> [--dry-run]")
        sys.exit(1)
    
    job_id = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("DRY RUN MODE - will generate LLM specs but not render videos")
    
    rerender_manim_sections(job_id, dry_run=dry_run)
