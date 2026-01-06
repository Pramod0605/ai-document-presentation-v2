import json
from pathlib import Path

JOB_ID = "d1c34c5f"
PROMPTS_PATH = Path(f"player/jobs/{JOB_ID}/render_prompts.json")

def inspect_prompts():
    if not PROMPTS_PATH.exists():
        print("❌ render_prompts.json NOT FOUND")
        return
        
    try:
        with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        print(f"✅ Loaded render_prompts.json ({len(str(data))} bytes)")
        
        if isinstance(data, list):
            print("Detected list format for render_prompts.json")
            # Usually list of dicts with keys like 'type' or implicit structure
            # Let's just print the first item keys to understand
            if data:
                print(f"Item 0 keys: {data[0].keys()}")
                manim = [x for x in data if x.get('type') == 'manim' or 'spec' in x]
                videos = [x for x in data if x.get('type') == 'video' or 'prompt' in x]
        else:
            # Dictionary format
            manim = data.get("manim_prompts", [])
            videos = data.get("video_prompts", [])
            
        print(f"Manim Specs: {len(manim)}")
        if manim:
            print(f"  Sample Spec [0]: {manim[0]['spec'][:100]}...")
            
        # Video Prompts
        videos = data.get("video_prompts", [])
        print(f"Video Prompts: {len(videos)}")
        if videos:
            print(f"  Sample Prompt [0]: {videos[0]['prompt'][:100]}...")
            
        # Check for pointers indirectly?
        # render_prompts usually just has the visual instructions.
        # But confirming this exists means the DIRECTOR SUCCEEDED.
        
        pass_check = len(manim) > 0 or len(videos) > 0
        if pass_check:
            print("\n🎉 PIPELINE STATUS: Director Stage Complete (Prompts Generated)")
        else:
             print("\n⚠️ PIPELINE STATUS: Director Stage Partial (No prompts found)")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_prompts()
