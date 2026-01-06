import json
import os
from pathlib import Path

JOB_ID = "512ecb49"
BASE_DIR = Path(f"player/jobs/{JOB_ID}")
JSON_PATH = BASE_DIR / "presentation.json"
MD_PATH = BASE_DIR / "source_markdown.md"

def inspect_job():
    print(f"Inspecting Job: {JOB_ID}")
    
    if not JSON_PATH.exists():
        print("❌ presentation.json NOT FOUND")
        return
        
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        with open(MD_PATH, "r", encoding="utf-8") as f:
            source_md = f.read()
            
        print(f"✅ Loaded JSON ({len(str(data))} bytes)")
        print(f"✅ Loaded Source Markdown ({len(source_md)} chars)")
        
        sections = data.get("sections", [])
        total_segments = 0
        pointer_segments = 0
        verified_pointers = 0
        
        print("\n--- Pointer Sample ---")
        
        for sec in sections:
            segments = sec.get("narration", {}).get("segments", [])
            for seg in segments:
                total_segments += 1
                vis = seg.get("visual_content", {})
                
                # Check for pointer
                pointer = vis.get("markdown_pointer")
                if pointer:
                    pointer_segments += 1
                    start = pointer.get("start_phrase", "")
                    end = pointer.get("end_phrase", "")
                    
                    if not start or not end:
                        print(f"⚠️ Empty pointer in {sec['section_id']}")
                        continue
                        
                    # Verify in source
                    start_found = start in source_md
                    end_found = end in source_md
                    
                    if start_found and end_found:
                        verified_pointers += 1
                        if verified_pointers == 1: # Print first good one
                            print(f"Found VALID Pointer in {sec['section_id']}:")
                            print(f"  Start: '{start[:40]}...'")
                            print(f"  End:   '{end[:40]}...'")
                    else:
                        print(f"❌ BROKEN Pointer in {sec['section_id']}")
                        if not start_found: print(f"  Target Start NOT found: '{start[:40]}...'")
                        if not end_found: print(f"  Target End NOT found: '{end[:40]}...'")

        print("\n--- Summary ---")
        print(f"Total Segments: {total_segments}")
        print(f"Segments with Pointers: {pointer_segments}")
        print(f"Verified Pointers: {verified_pointers}")
        
        if pointer_segments > 0 and verified_pointers == pointer_segments:
             print("\n🎉 RESULT: PASS - 100% Fidelity Achieved")
        elif pointer_segments > 0:
             print(f"\n⚠️ RESULT: PARTIAL - {verified_pointers}/{pointer_segments} valid")
        else:
             print("\n❌ RESULT: FAIL - No pointers generated")
             
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_job()
