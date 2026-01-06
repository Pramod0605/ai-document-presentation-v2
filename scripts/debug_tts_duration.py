import json
import logging
import sys
import os
from pathlib import Path

# Add current path
sys.path.insert(0, os.getcwd())

from core.tts_duration import update_durations_simplified

logging.basicConfig(level=logging.INFO)

JOB_ID = "5d0f14cd"
JOB_DIR = Path(f"player/jobs/{JOB_ID}")
PRES_FILE = JOB_DIR / "presentation.json"

def test_tts_update():
    print(f"Loading {PRES_FILE}...")
    try:
        with open(PRES_FILE, "r", encoding="utf-8") as f:
            presentation = json.load(f)
    except Exception as e:
        print(f"Failed to load JSON: {e}")
        return

    print("Checking initial state...")
    sections = presentation.get("sections", [])
    initial_zeros = 0
    for sec in sections:
        for seg in sec.get("narration", {}).get("segments", []):
            if seg.get("duration_seconds", 0) <= 0:
                initial_zeros += 1
    print(f"Initial 0s segments: {initial_zeros}")

    print("\nRunning update_durations_simplified() with provider='estimate'...")
    try:
        updated_pres = update_durations_simplified(
            presentation, 
            output_dir=JOB_DIR, 
            production_provider="estimate"
        )
        print("Function returned.")
    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\nChecking final state...")
    sections = updated_pres.get("sections", [])
    final_zeros = 0
    for sec in sections:
        for seg in sec.get("narration", {}).get("segments", []):
            if seg.get("duration_seconds", 0) <= 0:
                final_zeros += 1
                
    print(f"Final 0s segments: {final_zeros}")
    
    meta = updated_pres.get("metadata", {})
    print(f"Metadata Provider: {meta.get('tts_provider')}")
    
    if final_zeros == 0:
        print("SUCCESS: Durations updated correctly.")
    else:
        print("FAILURE: Durations stuck at 0.")

if __name__ == "__main__":
    test_tts_update()
