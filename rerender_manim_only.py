import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from core.renderer_executor import execute_renderer

def rerender_manim():
    job_id = '5f7e5f05'
    # Use absolute path for Windows reliability
    base_dir = Path(os.getcwd())
    job_dir = base_dir / 'player' / 'jobs' / job_id
    pres_path = job_dir / "presentation.json"
    
    print(f"--- Re-rendering Manim with ABSOLUTE PATHS ---")
    print(f"Job Dir: {job_dir}")
    
    with open(pres_path, 'r', encoding='utf-8') as f:
        presentation = json.load(f)
    
    sections = presentation.get('sections', [])
    for section in sections:
        if section.get('renderer') == 'manim':
            sec_id = section.get('section_id')
            print(f"  - Rendering Sec {sec_id}...")
            try:
                res = execute_renderer(section, str(job_dir), dry_run=False)
                print(f"    [RESULT] Sec {sec_id}: {res.get('status')}")
            except Exception as e:
                print(f"    [ERROR] Sec {sec_id} render failed: {e}")

if __name__ == "__main__":
    rerender_manim()
