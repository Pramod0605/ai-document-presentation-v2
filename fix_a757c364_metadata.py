import json
import os
from pathlib import Path

job_id = "a757c364"
# Assuming root of project
job_path = Path(f"player/jobs/{job_id}")
pres_path = job_path / "presentation.json"
analytics_path = job_path / "analytics.json"

if not pres_path.exists():
    print(f"Error: {pres_path} not found.")
    exit(1)

with open(pres_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# --- CONFIGURATION ---
# Map section_id -> video_path
videos = {
    "4": "topic_4.mp4",
    "5": "topic_5.mp4",
}

# Recap video beats (Topic 8)
recap_beats = [f"topic_8_beat_{i}.mp4" for i in range(5)]

# Avatars found on disk
avatars = {
    "1": "section_1_avatar.mp4",
    "2": "section_2_avatar.mp4",
    "3": "section_3_avatar.mp4",
    "6": "section_6_avatar.mp4",
    "7": "section_7_avatar.mp4",
    "8": "section_8_avatar.mp4",
}

updated_sections = []

for section in data.get("sections", []):
    sid = str(section.get("section_id"))
    changed = False
    
    # 1. Handle Main Video
    if sid in videos:
        section["video_path"] = f"videos/{videos[sid]}"
        changed = True
        
    # 2. Handle Recap Beats
    if sid == "8":
        section["video_path"] = f"videos/{recap_beats[0]}"
        section["beat_videos"] = [f"videos/{b}" for b in recap_beats]
        section["recap_video_paths"] = [f"videos/{b}" for b in recap_beats]
        changed = True
        
    # 3. Handle Avatars
    if sid in avatars:
        section["avatar_video"] = f"avatars/{avatars[sid]}"
        section["avatar_status"] = "completed"
        changed = True
        
    if changed:
        updated_sections.append(sid)

if updated_sections:
    with open(pres_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"✅ Successfully updated presentation.json for sections: {', '.join(updated_sections)}")
else:
    print("ℹ️ No updates needed for presentation.json")

# --- UPDATE ANALYTICS ---
if analytics_path.exists():
    with open(analytics_path, 'r', encoding='utf-8') as f:
        analytics = json.load(f)
    
    # Hard-fix renderer counts
    if "renderer" not in analytics:
        analytics["renderer"] = {"manim_videos": 0, "wan_videos": 0, "failed_renders": 0, "section_renders": []}
    
    analytics["renderer"]["wan_videos"] = 3 # Topics 4, 5, 8
    
    # Hard-fix avatar counts
    if "avatar" not in analytics:
        analytics["avatar"] = {"successful_sections": 0, "total_sections": 0, "section_details": []}
    
    analytics["avatar"]["successful_sections"] = len(avatars)
    
    with open(analytics_path, 'w', encoding='utf-8') as f:
        json.dump(analytics, f, indent=2)
    print(f"✅ Successfully updated analytics.json")

print("\n🚀 Repair script finished. Please refresh the Sanity Check page.")
