import json
import os
from pathlib import Path

def inspect():
    job_id = '5f7e5f05'
    pres_path = Path(f'player/jobs/{job_id}/presentation.json')
    py_path = Path(f'player/jobs/{job_id}/manim_code/section_10.py')
    video_path = Path(f'player/jobs/{job_id}/videos/topic_10.mp4')
    
    print(f"--- Inspection for Job {job_id} Section 10 ---")
    
    if pres_path.exists():
        with open(pres_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        sec = next((s for s in data.get('sections', []) if s.get('section_id') == 10), None)
        if sec:
            print(f"JSON Status: {sec.get('status')}")
            print(f"JSON Renderer: {sec.get('renderer')}")
            print(f"JSON Render Error: {sec.get('render_error')}")
            rs = sec.get('render_spec', {})
            mss = rs.get('manim_scene_spec', {})
            code = mss.get('manim_code', '')
            print(f"JSON Code Length: {len(code)}")
            if code:
                print(f"JSON Code Tail: {repr(code[-100:])}")
            else:
                # Try top level just in case
                code_top = sec.get('manim_code', '')
                if code_top:
                    print(f"JSON Code Length (Top Level): {len(code_top)}")
        else:
            print("Section 10 not found in JSON")
            
    print(f"Python File Exists: {py_path.exists()}")
    if py_path.exists():
        content = py_path.read_text(encoding='utf-8')
        print(f"Python File Length: {len(content)}")
        print(f"Python File Tail: {repr(content[-100:])}")
        
    print(f"Video File Exists: {video_path.exists()}")

if __name__ == "__main__":
    inspect()
