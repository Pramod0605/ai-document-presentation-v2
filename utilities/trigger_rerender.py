"""
Trigger WAN Video Re-render for a specific job.
Uses KieBatchGenerator for proper 15-batch processing with 15s intervals.
"""
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# Load environmental variables from .env file
load_dotenv(PROJECT_ROOT / ".env", override=True)

from render.wan.kie_batch_generator import KieBatchGenerator

JOB_ID = "48808436"
JOB_PATH = PROJECT_ROOT / "player" / "jobs" / JOB_ID
PRESENTATION_PATH = JOB_PATH / "presentation.json"
VIDEOS_DIR = JOB_PATH / "videos"

def collect_wan_prompts():
    """Collect all WAN prompts from presentation.json that need videos."""
    with open(PRESENTATION_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    beats_to_render = []
    
    for section in data.get("sections", []):
        renderer = section.get("renderer", "").lower()
        if renderer not in ["video", "wan"]:
            continue
        
        video_prompts = section.get("video_prompts", [])
        for vp in video_prompts:
            beat_id = vp.get("beat_id")
            prompt = vp.get("prompt")
            duration = vp.get("duration_hint", vp.get("duration", 15))
            
            if not beat_id or not prompt:
                continue
            
            # Check if video already exists
            video_path = VIDEOS_DIR / f"{beat_id}.mp4"
            if video_path.exists() and video_path.stat().st_size > 10000:
                print(f"  [SKIP] {beat_id} already exists ({video_path.stat().st_size} bytes)")
                continue
            
            beats_to_render.append({
                "beat_id": beat_id,
                "prompt": prompt,
                "duration_hint": duration
            })
    
    return beats_to_render

def main():
    print(f"=== WAN Re-render Trigger (Job {JOB_ID}) ===")
    print(f"Presentation: {PRESENTATION_PATH}")
    print(f"Output Dir: {VIDEOS_DIR}")
    print()
    
    if not PRESENTATION_PATH.exists():
        print(f"ERROR: {PRESENTATION_PATH} not found")
        return
    
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Collect prompts
    beats = collect_wan_prompts()
    print(f"Found {len(beats)} beats to render.\n")
    
    if not beats:
        print("All videos already exist. Nothing to render.")
        return
    
    # Use batch generator
    generator = KieBatchGenerator()
    print(f"Starting batched generation (batch_size={generator.BATCH_SIZE}, interval={generator.BATCH_INTERVAL}s)...\n")
    
    results = generator.generate_batch(beats, str(VIDEOS_DIR))
    
    # Summary
    success_count = sum(1 for v in results.values() if v and not v.endswith("_placeholder.mp4"))
    print(f"\n=== RESULTS ===")
    print(f"Total: {len(beats)}")
    print(f"Success: {success_count}")
    print(f"Failed/Placeholder: {len(beats) - success_count}")

if __name__ == "__main__":
    main()
