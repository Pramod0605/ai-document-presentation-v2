import json
import os
import sys
from pathlib import Path

# Target Job
JOB_ID = "6b12114f"
BASE_DIR = Path(f"player/jobs/{JOB_ID}")
JSON_PATH = BASE_DIR / "presentation.json"
MD_PATH = BASE_DIR / "source_markdown.md"
AUDIO_DIR = BASE_DIR / "audio"

def generate_report():
    print(f"==================================================")
    print(f"   JOB REPORT: {JOB_ID}")
    print(f"==================================================")

    # 1. EXISTENCE CHECK
    if not BASE_DIR.exists():
        print(f"❌ Job Directory Not Found")
        return
    
    if not JSON_PATH.exists():
        print(f"⚠️  STATUS: PROCESSING")
        print(f"   presentation.json has not been written yet.")
        print(f"   The pipeline is likely in the Rendering or TTS phase.")
        
        # Check for partial artifacts
        prompts = BASE_DIR / "render_prompts.json"
        if prompts.exists():
            print(f"   ✅ Partial Success: 'render_prompts.json' exists (Director finished).")
        return

    # Load Data
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ JSON Load Warning: {e}")
        return

    # 2. METADATA & PIPELINE MODE
    meta = data.get("metadata", {})
    gen_by = meta.get("generated_by", "UNKNOWN")
    print(f"\n[1] PIPELINE CONFIGURATION")
    print(f"   • Generator:   {gen_by}")
    
    if gen_by == "v1.5-v2.5-director":
        print(f"   ✅ PASS: Correct V2.5 Director Mode active.")
    else:
        print(f"   ❌ FAIL: Legacy generator detected ('{gen_by}').")

    # 3. CONTENT FIDELITY (POINTERS)
    print(f"\n[2] CONTENT FIDELITY (POINTERS)")
    sections = data.get("sections", [])
    total_segments = 0
    pointer_segments = 0
    legacy_segments = 0
    
    md_content = ""
    if MD_PATH.exists():
        try:
            with open(MD_PATH, "r", encoding="utf-8") as f:
                md_content = f.read()
        except: pass

    for sec in sections:
        narration = sec.get("narration", {})
        for seg in narration.get("segments", []):
            total_segments += 1
            vis = seg.get("visual_content", {})
            
            # Check for Pointer
            ptr = vis.get("markdown_pointer")
            if ptr:
                pointer_segments += 1
                # Verify resolution if MD exists
                if md_content:
                    start = ptr.get("start_phrase", "")
                    end = ptr.get("end_phrase", "")
                    if start in md_content and end in md_content:
                        pass # Valid
                    else:
                        print(f"      ⚠️  Warning: Pointer phrases not found in source MD (Seg {seg.get('segment_id')})")
            
            # Check for Legacy Leakage
            if "display_text" in vis or "visual_beats" in sec:
                legacy_segments += 1

    print(f"   • Total Segments: {total_segments}")
    print(f"   • Pointers Found: {pointer_segments}")
    
    if pointer_segments > 0:
         print(f"   ✅ PASS: Pointers are present ({pointer_segments}/{total_segments}).")
    else:
         print(f"   ❌ FAIL: Zero pointers found. Legacy output.")

    if legacy_segments > 0:
        print(f"   ⚠️  Warning: {legacy_segments} legacy fields detected (mixed schema).")

    # 4. AUDIO WIRING
    print(f"\n[3] AUDIO WIRING")
    sections_with_audio = 0
    audio_files_exist = 0
    
    for sec in sections:
        audio_path = sec.get("audio_path")
        if audio_path:
            sections_with_audio += 1
            # Check physical file
            # Player expects path relative to job dir? Or absolute? 
            # Usually "audio/section_1.mp3"
            local_path = BASE_DIR / audio_path
            if local_path.exists():
                audio_files_exist += 1
        else:
            print(f"   ❌ Section '{sec.get('title')}' missing 'audio_path'")

    print(f"   • Wired Sections: {sections_with_audio}/{len(sections)}")
    print(f"   • Valid Files:    {audio_files_exist}/{len(sections)}")
    
    if sections_with_audio == len(sections):
        print(f"   ✅ PASS: All sections have audio attached.")
    else:
        print(f"   ❌ FAIL: Audio wiring incomplete.")

    # 5. FINAL VERDICT
    print(f"\n[4] FINAL VERDICT")
    if gen_by == "v1.5-v2.5-director" and pointer_segments > 0 and sections_with_audio == len(sections):
        print(f"   🎉 SUCCESS: JOB IS VALID V2.5 DIRECTOR OUTPUT")
    else:
        print(f"   ⛔ FAILED: See details above.")

if __name__ == "__main__":
    generate_report()
