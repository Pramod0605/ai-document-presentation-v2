import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from api.app import JOBS_DIR
from core.agents.manim_code_generator import ManimCodeGenerator, integrate_manim_code_into_section
from core.renderer_executor import execute_renderer

def repair_and_render_sec10():
    job_id = '5f7e5f05'
    section_id = 10
    
    job_dir = Path(r'player/jobs') / job_id
    pres_path = job_dir / "presentation.json"
    
    print(f"Repairing Job {job_id} Section {section_id}...")
    
    with open(pres_path, 'r', encoding='utf-8') as f:
        presentation = json.load(f)
    
    section = next((s for s in presentation.get('sections', []) if s.get('section_id') == section_id), None)
    if not section:
        print("Section not found")
        return
    
    # Transform data for generator
    nar = section.get("narration", {})
    segments = nar.get("segments", [])
    render_spec = section.get("render_spec", {})
    manim_spec = render_spec.get("manim_scene_spec")
    if isinstance(manim_spec, dict):
        manim_spec = manim_spec.get("description", "")
    
    section_data = {
        "section_title": section.get("title", "Section"),
        "narration_segments": segments,
        "manim_spec": manim_spec or section.get("explanation_plan", ""),
    }
    
    # 1. Regenerate Code with my new validation logic
    print("Regenerating code...")
    manim_gen = ManimCodeGenerator()
    code = manim_gen.generate_code(section_data)
    
    if not code or len(code) < 100:
        print("Generation failed or too short")
        return
    
    # 2. Update Files
    print("Updating files...")
    code_file = job_dir / "manim_code" / f"section_{section_id}.py"
    code_file.parent.mkdir(exist_ok=True)
    with open(code_file, "w", encoding="utf-8") as f:
        f.write(code)
    
    integrate_manim_code_into_section(section, code)
    
    # 3. Save JSON
    with open(pres_path, "w", encoding="utf-8") as f:
        json.dump(presentation, f, indent=4)
    
    # 4. Trigger Render
    print("Triggering render...")
    res = execute_renderer(section, job_id, str(job_dir))
    print(f"Render Result: {res}")
    
    # Final check
    video_path = job_dir / "videos" / f"topic_{section_id}.mp4"
    print(f"Video created: {video_path.exists()}")

if __name__ == "__main__":
    repair_and_render_sec10()
