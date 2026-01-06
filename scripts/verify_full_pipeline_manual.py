import sys
import os
import json
import logging
from pathlib import Path

# Force Path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Configure Logging
logging.basicConfig(level=logging.INFO)

# Imports
from core.pipeline_unified import process_markdown_unified
from core.analytics import create_tracker

# Mock Data
MOCK_MARKDOWN = """
# Arithmetic Progressions

## Introduction
An arithmetic progression is a sequence of numbers where the differences between every two consecutive terms is constant.

## Formula
The nth term is given by $a_n = a + (n-1)d$.

## Summary
* AP has constant difference.
* Formula is linear.
"""

JOB_ID = "manual_verify_001"
OUTPUT_DIR = Path(f"player/jobs/{JOB_ID}")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def mock_callback(jid, phase, msg):
    print(f"[{phase}] {msg}")

print(f"🚀 Starting MANUAL Full Pipeline Check for {JOB_ID}...")

try:
    # 1. Run Pipeline
    presentation, tracker = process_markdown_unified(
        markdown_content=MOCK_MARKDOWN,
        subject="Math",
        grade="10",
        job_id=JOB_ID,
        output_dir=OUTPUT_DIR,
        update_status_callback=mock_callback,
        pipeline_version="v15_v2_director", # FORCE V2.5 PARALLEL
        generate_tts=True, # TEST TTS
        tts_provider="edge_tts" 
    )
    
    # 2. Verify Output
    print("\n✅ Pipeline Finished. Verifying Assets...")
    
    # Check JSON
    json_path = OUTPUT_DIR / "presentation.json"
    if json_path.exists():
        print(f"✅ presentation.json saved ({json_path.stat().st_size} bytes)")
    else:
        print("❌ presentation.json MISSING (Did it crash?)")

    # Check Audio
    audio_dir = OUTPUT_DIR / "audio"
    if audio_dir.exists():
        files = list(audio_dir.glob("*.mp3"))
        print(f"✅ Audio Files Generated: {len(files)}")
        for f in files[:3]:
            print(f"   - {f.name}")
    else:
        print("❌ Audio Directory Missing (TTS Failed)")

    # Check Manim Code
    manim_found = False
    for sec in presentation.get("sections", []):
        if sec.get("renderer") == "manim":
            code = sec.get("manim_code", "")
            if code:
                print(f"✅ Manim Code Found in '{sec.get('title')}' ({len(code)} chars)")
                manim_found = True
            else:
                print(f"⚠️ Manim Section '{sec.get('title')}' has NO CODE.")
    
    if not manim_found:
        print("⚠️ No Manim sections generated (Using mock markdown might be too simple?)")

except Exception as e:
    print(f"\n❌ CRASHED: {e}")
    import traceback
    traceback.print_exc()
