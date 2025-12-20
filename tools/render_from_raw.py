#!/usr/bin/env python3
"""
Render Manim videos from saved raw LLM response JSON files.
Usage: python tools/render_from_raw.py <job_id>
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from render.manim.manim_runner import render_manim_video, ManimRenderError

def render_from_raw_responses(job_id: str):
    """Read raw LLM responses and render Manim videos."""
    job_dir = Path(f"player/jobs/{job_id}")
    llm_responses_dir = job_dir / "llm_responses"
    videos_dir = job_dir / "videos"
    
    if not llm_responses_dir.exists():
        print(f"Error: No llm_responses folder for job {job_id}")
        return
    
    videos_dir.mkdir(exist_ok=True)
    
    manim_files = sorted(llm_responses_dir.glob("manim_*.json"))
    
    if not manim_files:
        print(f"No Manim raw response files found in {llm_responses_dir}")
        return
    
    print(f"Found {len(manim_files)} Manim response files")
    
    rendered = []
    failed = []
    
    for raw_file in manim_files:
        print(f"\n{'='*60}")
        print(f"Processing: {raw_file.name}")
        
        try:
            with open(raw_file) as f:
                raw_data = json.load(f)
            
            section_id = raw_data.get("section_id", "unknown")
            raw_response = raw_data.get("raw_response", "")
            
            llm_output = json.loads(raw_response)
            manim_scene_spec = llm_output.get("manim_scene_spec")
            
            if not manim_scene_spec:
                print(f"  No manim_scene_spec found in {raw_file.name}")
                failed.append((raw_file.name, "No manim_scene_spec"))
                continue
            
            objects = manim_scene_spec.get("objects", [])
            animations = manim_scene_spec.get("animation_sequence", [])
            
            total_duration = sum(
                a.get("duration", 1) for a in animations
            )
            
            print(f"  Section: {section_id}")
            print(f"  Objects: {len(objects)}")
            print(f"  Animations: {len(animations)}")
            print(f"  Estimated duration: {total_duration}s")
            
            topic = {
                "section_id": section_id,
                "title": f"Section {section_id}",
                "section_type": "content",
                "duration": max(total_duration, 10),
                "explanation_plan": {
                    "v12_manim_scene_spec": manim_scene_spec
                }
            }
            
            result = render_manim_video(
                topic=topic,
                output_dir=str(videos_dir),
                dry_run=False,
                trace_output_dir=str(job_dir)
            )
            
            print(f"  SUCCESS: {result}")
            rendered.append((section_id, result))
            
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            failed.append((raw_file.name, f"JSON error: {e}"))
        except ManimRenderError as e:
            print(f"  Manim render error: {e}")
            failed.append((raw_file.name, str(e)))
        except Exception as e:
            print(f"  Unexpected error: {e}")
            failed.append((raw_file.name, str(e)))
    
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Rendered: {len(rendered)}")
    for section_id, path in rendered:
        print(f"  - {section_id}: {path}")
    
    if failed:
        print(f"\nFailed: {len(failed)}")
        for name, reason in failed:
            print(f"  - {name}: {reason}")
    
    return rendered, failed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/render_from_raw.py <job_id>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    render_from_raw_responses(job_id)
