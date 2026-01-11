import os
import json
import sys
from pathlib import Path

def fix_paths(job_dir):
    job_path = Path(job_dir)
    json_path = job_path / "presentation.json"
    
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        return

    print(f"Scanning {json_path}...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    avatars_dir = job_path / "avatars"
    videos_dir = job_path / "videos"
    images_dir = job_path / "images"
    
    updates = 0

    for section in data.get("sections", []):
        sec_id = section.get("section_id")
        
        # 1. FIX AVATAR PATHS
        avatar_val = section.get("avatar_video") or section.get("avatar_video_path")
        if avatar_val:
            # Extract basic filename
            filename = os.path.basename(avatar_val)
            # Check if exists in avatars dir
            if (avatars_dir / filename).exists():
                new_path = f"avatars/{filename}"
                if section.get("avatar_video") != new_path:
                    print(f"Sec {sec_id}: Fixing Avatar {avatar_val} -> {new_path}")
                    section["avatar_video"] = new_path
                    updates += 1
            else:
                print(f"Sec {sec_id}: Warning - Avatar {filename} not found in {avatars_dir}")

        # 2. FIX VIDEO PATHS
        video_val = section.get("video_path")
        if video_val:
            # Handle the crazy double path case "videos/C:\..."
            # os.path.basename handles mixed slashes well usually
            clean_name = os.path.basename(video_val.replace("\\", "/"))
            if (videos_dir / clean_name).exists():
                new_path = f"videos/{clean_name}"
                if section.get("video_path") != new_path:
                    print(f"Sec {sec_id}: Fixing Video {video_val} -> {new_path}")
                    section["video_path"] = new_path
                    updates += 1

        # 3. FIX IMAGE PATHS in VISUAL BEATS
        if "visual_beats" in section:
            for beat in section["visual_beats"]:
                if beat.get("visual_type") in ["image", "diagram"]:
                    img_id = beat.get("image_id") or beat.get("image_path")
                    if img_id:
                        # Normalize ID (strip path if present)
                        clean_id = os.path.basename(img_id)
                        name_no_ext, ext = os.path.splitext(clean_id)
                        
                        # Check exact match
                        if (images_dir / clean_id).exists():
                             # Just ensure path is clean if it was full path
                             if img_id != clean_id:
                                 beat["image_id"] = clean_id
                                 updates += 1
                        else:
                            # Check extension swap
                            possible_exts = [".png", ".jpg", ".jpeg", ".webp"]
                            found = False
                            for e in possible_exts:
                                test_name = name_no_ext + e
                                if (images_dir / test_name).exists():
                                    print(f"Sec {sec_id}: Fixing Image Extension {clean_id} -> {test_name}")
                                    beat["image_id"] = test_name
                                    beat["image_path"] = test_name # consistency
                                    updates += 1
                                    found = True
                                    break
                            
                            if not found:
                                print(f"Sec {sec_id}: Warning - Image {clean_id} not found in {images_dir}")

    if updates > 0:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"\nSaved {updates} path corrections to presentation.json")
    else:
        print("\nNo changes needed.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_presentation_paths.py <job_dir>")
        sys.exit(1)
    
    fix_paths(sys.argv[1])
