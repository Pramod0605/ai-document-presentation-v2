import json
import re
import sys
from pathlib import Path

# Usage: python scripts/verify_job_fidelity.py [JOB_ID]
JOB_ID = "dd435125" # Hardcoded for check
if len(sys.argv) > 1:
    JOB_ID = sys.argv[1]
else:
    # Auto-detect latest
    try:
        jobs_dir = Path("player/jobs")
        all_jobs = [d for d in jobs_dir.iterdir() if d.is_dir()]
        all_jobs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        JOB_ID = all_jobs[0].name
    except:
        JOB_ID = "UNKNOWN"

JOB_DIR = Path(f"player/jobs/{JOB_ID}")

def print_pass(msg):
    print(f"✅ PASS: {msg}")

def print_fail(msg):
    print(f"❌ FAIL: {msg}")

def print_warn(msg):
    print(f"⚠️ WARN: {msg}")

def analyze_fidelity():
    print(f"\n====== 🔍 JOB FIDELITY REPORT: {JOB_ID} ======\n")
    
    # 1. Load Files
    try:
        with open(JOB_DIR / "presentation.json", "r", encoding="utf-8") as f:
            pres = json.load(f)
        with open(JOB_DIR / "source_markdown.md", "r", encoding="utf-8") as f:
            source = f.read()
        print(f"📂 Loaded presentation.json and source_markdown.md")
    except FileNotFoundError as e:
        print_fail(f"Missing file - {e}")
        return

    sections = pres.get("sections", [])
    
    # 2. Key Architecture Successes
    print(f"\n--- 🏗️ ARCHITECTURE CHECK ---")
    meta = pres.get("metadata", {})
    chunks = meta.get("chunks", 0)
    if chunks > 0:
        print_pass(f"Partitioning Active: {chunks} chunks processed")
    else:
        print_fail("Partitioning failed (0 chunks recorded)")
        
    doc_len = meta.get("doc_length", 0)
    print_pass(f"Document Size: {doc_len} chars")

    print(f"Meta: TTS Provider={meta.get('tts_provider')}, Audio Provider={meta.get('audio_provider')}")
    print(f"Meta: Duration Provider={meta.get('duration_provider')}")

    # 3. The Critical Fix: Narration Structure
    print(f"\n--- 🗣️ NARRATION CHECK (The Fix) ---")
    narration_valid = 0
    narration_missing = 0
    zero_durations = 0
    
    for i, sec in enumerate(sections):
        if sec.get("section_type") == "content":
            narr = sec.get("narration")
            if not narr or not isinstance(narr, dict):
                narration_missing += 1
                continue
                
            segments = narr.get("segments", [])
            if not segments:
                narration_missing += 1
                continue
                
            narration_valid += 1
            
            # Check durations inside
            for seg in segments:
                if seg.get("duration_seconds", 0) <= 0:
                    zero_durations += 1

    if narration_missing == 0 and narration_valid > 0:
        print_pass(f"All {narration_valid} content sections have valid Narration objects.")
    elif narration_valid > 0:
        print_warn(f"{narration_missing} sections missing narration, {narration_valid} valid.")
    else:
        print_fail("NO valid narration objects found! (Prompt failed)")

    # 4. Duration Logic
    if zero_durations == 0 and narration_valid > 0:
        print_pass("Duration Calculation Fix Verified (All segments > 0s)")
    elif narration_valid > 0:
        print_fail(f"{zero_durations} segments still have 0s duration.")

    # 5. Content Coverage
    print(f"\n--- 📚 CONTENT COMPLETENESS ---")
    source_headers = re.findall(r'^##\s+(.+)$', source, re.MULTILINE)
    gen_titles = [s.get("title") for s in sections]
    
    matched = 0
    for h in source_headers:
        if any(h.lower() in t.lower() or t.lower() in h.lower() for t in gen_titles):
            matched += 1
            
    coverage = (matched / len(source_headers)) * 100 if source_headers else 0
    print(f"Header coverage: {matched}/{len(source_headers)} ({coverage:.1f}%)")
    
    print("\n====== END REPORT ======")

if __name__ == "__main__":
    analyze_fidelity()
