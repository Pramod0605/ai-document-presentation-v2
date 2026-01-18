import json
import os
from pathlib import Path
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from render.wan.wan_client import WANClient

JOB_ID = "48808436"
JOB_DIR = Path(f"player/jobs/{JOB_ID}")
PRESENTATION_PATH = JOB_DIR / "presentation.json"
VIDEOS_DIR = JOB_DIR / "videos"

def render_missing_visuals():
    if not PRESENTATION_PATH.exists():
        print(f"Error: {PRESENTATION_PATH} not found.")
        return

    with open(PRESENTATION_PATH, "r", encoding="utf-8") as f:
        presentation = json.load(f)

    sections_to_process = [3, 4, 5, 11] # Adding 11 as well as it was mentioned in render_prompts.json
    # Filter for Sections 3, 4, 5
    topics = [t for t in presentation.get("sections", []) if t.get("section_id") in [3, 4, 5]]
    
    print(f"Found {len(topics)} target sections (3, 4, 5).")
    
    client = WANClient()
    
    for topic in topics:
        section_id = topic.get("section_id")
        title = topic.get("title")
        print(f"\nProcessing Section {section_id}: {title}")
        
        video_prompts = topic.get("video_prompts", [])
        if not video_prompts:
            print(f"  No video_prompts found for section {section_id}.")
            continue
            
        for vp in video_prompts:
            beat_id = vp.get("beat_id")
            prompt = vp.get("prompt")
            duration = vp.get("duration", 8)
            
            if not beat_id or not prompt:
                continue
                
            # Clean beat_id for filename
            filename = f"{beat_id}.mp4"
            output_path = VIDEOS_DIR / filename
            
            print(f"  Checking {filename}...")
            
            if output_path.exists():
                print(f"    [SKIP] Already exists: {filename}")
                continue
                
            # Cap duration for WAN (5-15s)
            capped_duration = max(5, min(15, int(duration)))
            
            print(f"    [GENERATE] Providing prompt for {filename} ({capped_duration}s)...")
            print(f"    Prompt: {prompt[:100]}...")
            
            try:
                # In a real run, uncomment this
                result = client.generate_video(
                    prompt=prompt,
                    duration=capped_duration,
                    output_path=str(output_path)
                )
                print(f"    [SUCCESS] Saved to {result}")
            except Exception as e:
                print(f"    [ERROR] Failed to generate {filename}: {e}")

if __name__ == "__main__":
    render_missing_visuals()
