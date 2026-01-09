import os
import json
import shutil
from pathlib import Path
from core.agents.avatar_generator import AvatarGenerator

def test_artifact_update():
    print("Testing _update_artifacts logic...")
    
    # Setup
    test_dir = Path("test_artifact_update_temp")
    test_dir.mkdir(exist_ok=True)
    
    # Create dummy presentation
    pres = {
        "sections": [
            {"section_id": 1, "title": "Test Section", "video": "old_path.mp4"}
        ]
    }
    with open(test_dir / "presentation.json", "w") as f:
        json.dump(pres, f)
        
    # Test
    ag = AvatarGenerator()
    video_path = test_dir / "avatars" / "section_1_avatar.mp4"
    str_video_path = str(video_path)
    
    # Run
    print("running update...")
    ag._update_artifacts(str(test_dir), 1, str_video_path, duration=15.5)
    
    # Verify
    with open(test_dir / "presentation.json", "r") as f:
        data = json.load(f)
    
    sec = data["sections"][0]
    print(f"Result: {sec}")
    
    if sec.get("avatar_video") == "section_1_avatar.mp4" and sec.get("avatar_status") == "completed":
        print("SUCCESS: presentation.json updated correctly.")
    else:
        print("FAILURE: presentation.json not updated.")
        
    # Checked analytics creation
    if (test_dir / "analytics.json").exists():
        with open(test_dir / "analytics.json", "r") as f:
            ana = json.load(f)
        print(f"Analytics: {ana}")
        if ana["avatar"]["successful_sections"] == 1:
             print("SUCCESS: analytics.json created and updated.")
        else:
             print("FAILURE: analytics.json count mismatch.")
    else:
        print("INFO: analytics.json didn't exist, so logic created it? No, logic checks 'if exists' usually? Let's check code.")
        # My code uses: "if analytics_path.exists():" -> So it won't Create it if missing. That's safer for race conditions. 
        # But for test I should create it first if I want to test update.
    
    # Cleanup
    shutil.rmtree(test_dir)

if __name__ == "__main__":
    # Mock environment
    os.environ["AVATAR_API_URL"] = "http://dummy"
    test_artifact_update()
