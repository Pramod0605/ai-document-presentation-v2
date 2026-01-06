import json
import os
from pathlib import Path

JOB_ID = "512ecb49"
BASE_DIR = Path(f"player/jobs/{JOB_ID}")
JSON_PATH = BASE_DIR / "presentation.json"

def inspect_structure():
    if not JSON_PATH.exists():
        print("❌ presentation.json NOT FOUND")
        return
        
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    sections = data.get("sections", [])
    if not sections:
        print("No sections found")
        return
        
    print("--- First Section Structure ---")
    sec = sections[0]
    print(f"Keys: {list(sec.keys())}")
    
    if "audio_path" in sec:
        print(f"✅ audio_path found: {sec['audio_path']}")
    else:
        print("❌ audio_path MISSING in section")

    if "narration" in sec:
        narr = sec["narration"]
        print(f"Narration Keys: {list(narr.keys())}")
        if "segments" in narr:
            segs = narr["segments"]
            print(f"Segment Count: {len(segs)}")
            if segs:
                print("--- First Segment Structure ---")
                print(json.dumps(segs[0], indent=2))
    
    if "visual_beats" in sec:
         print("--- First Visual Beat ---")
         beats = sec["visual_beats"]
         if beats:
             print(json.dumps(beats[0], indent=2))

if __name__ == "__main__":
    inspect_structure()
