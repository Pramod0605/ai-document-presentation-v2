import json
import sys
from pathlib import Path

def verify_job(job_id):
    base_dir = Path(f"player/jobs/{job_id}")
    json_path = base_dir / "presentation.json"
    md_path = base_dir / "source_markdown.md"
    
    print(f"DIAGNOSTIC REPORT FOR JOB: {job_id}")
    print("-" * 40)

    if not json_path.exists():
        print("❌ presentation.json MISSING")
        return False
        
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 1. Check Pointers
        sections = data.get("sections", [])
        total_segments = 0
        pointer_count = 0
        audio_path_count = 0
        
        md_content = ""
        if md_path.exists():
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()

        print(f"Markdown Source: {'✅ Found' if md_content else '❌ Missing'}")
        
        for sec in sections:
            # Check Audio Path
            if "audio_path" in sec:
                audio_path_count += 1
            
            # Check Segments for Pointers
            for seg in sec.get("narration", {}).get("segments", []):
                total_segments += 1
                vis = seg.get("visual_content", {})
                ptr = vis.get("markdown_pointer")
                
                if ptr and ptr.get("start_phrase") and ptr.get("end_phrase"):
                    pointer_count += 1
                    
        print(f"\n1. POINTER CHECK:")
        if pointer_count > 0:
            print(f"   ✅ PASS: Found {pointer_count}/{total_segments} segments with pointers.")
        else:
            print(f"   ❌ FAIL: Zero pointers found. (Legacy Schema detected)")

        print(f"\n2. TTS WIRING CHECK:")
        if audio_path_count == len(sections):
            print(f"   ✅ PASS: All {audio_path_count} sections have 'audio_path'.")
        else:
            print(f"   ❌ FAIL: Only {audio_path_count}/{len(sections)} sections have audio links.")

        return pointer_count > 0 and audio_path_count == len(sections)

    except Exception as e:
        print(f"❌ Error inspecting file: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_latest_job.py <job_id>")
    else:
        verify_job(sys.argv[1])
