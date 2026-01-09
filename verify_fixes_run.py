import json
import os
import sys
import time
from pathlib import Path
from threading import Thread

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from api.app import JOBS_DIR, run_avatar_sequential_task
from core.agents.manim_code_generator import ManimCodeGenerator, integrate_manim_code_into_section
from core.renderer_executor import execute_renderer

def run_verification():
    job_id = '5f7e5f05'
    job_dir = Path(r'player/jobs') / job_id
    pres_path = job_dir / "presentation.json"
    
    print(f"--- Starting Final Verification for Job {job_id} ---")
    
    if not pres_path.exists():
        print("Presentation JSON not found!")
        return

    with open(pres_path, 'r', encoding='utf-8') as f:
        presentation = json.load(f)
    
    manim_gen = ManimCodeGenerator()
    sections = presentation.get('sections', [])
    
    # 1. Regenerate Manim Code for all Manim sections
    print("\n[STEP 1] Regenerating Manim Code...")
    for section in sections:
        if section.get('renderer') == 'manim':
            sec_id = section.get('section_id')
            print(f"  - Regenerating Sec {sec_id}...")
            
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
            
            try:
                code = manim_gen.generate_code(section_data)
                if code:
                    # Update file system
                    code_file = job_dir / "manim_code" / f"section_{sec_id}.py"
                    code_file.parent.mkdir(exist_ok=True)
                    with open(code_file, "w", encoding="utf-8") as f:
                        f.write(code)
                    
                    # Update JSON structure
                    integrate_manim_code_into_section(section, code)
                    print(f"    [SUCCESS] Sec {sec_id} code updated.")
            except Exception as e:
                print(f"    [FAILED] Sec {sec_id}: {e}")

    # Save updated presentation.json before rendering
    with open(pres_path, "w", encoding="utf-8") as f:
        json.dump(presentation, f, indent=4)

    # 2. Trigger Sequential Avatar Generation in Background
    print("\n[STEP 2] Launching Sequential Avatar Task...")
    avatar_thread = Thread(target=run_avatar_sequential_task, args=(job_id, str(JOBS_DIR.parent)))
    avatar_thread.daemon = True
    avatar_thread.start()
    print("  - Avatar task running in background.")

    # 3. Render Manim Videos
    print("\n[STEP 3] Rendering Manim Videos...")
    for section in sections:
        if section.get('renderer') == 'manim':
            sec_id = section.get('section_id')
            print(f"  - Rendering Sec {sec_id}...")
            try:
                # We pass dry_run=False to ensure real rendering
                res = execute_renderer(section, str(job_dir), dry_run=False)
                print(f"    [RESULT] Sec {sec_id}: {res.get('status')}")
            except Exception as e:
                print(f"    [ERROR] Sec {sec_id} render failed: {e}")

    # Final Save
    with open(pres_path, "w", encoding="utf-8") as f:
        json.dump(presentation, f, indent=4)
        
    print("\n--- Verification Run Initiated ---")
    print("Check avatar_status.json for Avatar progress.")
    print("Watch the console for Manim render outputs.")

if __name__ == "__main__":
    run_verification()
