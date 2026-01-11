#!/usr/bin/env python3
"""
Utility: Patch presentation.json with missing avatar_video paths.
Scans the avatars folder and updates presentation.json for sections with missing avatar_video.
"""
import json
import os
import sys
from pathlib import Path

def patch_avatar_paths(job_dir: str):
    job_path = Path(job_dir)
    pres_path = job_path / "presentation.json"
    avatars_dir = job_path / "avatars"
    
    if not pres_path.exists():
        print(f"ERROR: presentation.json not found at {pres_path}")
        return False
    
    if not avatars_dir.exists():
        print(f"WARNING: avatars folder not found at {avatars_dir}")
        return False
    
    # Load presentation
    with open(pres_path, 'r', encoding='utf-8') as f:
        pres = json.load(f)
    
    # Scan avatar files
    avatar_files = list(avatars_dir.glob("section_*_avatar.mp4"))
    print(f"Found {len(avatar_files)} avatar files")
    
    # Build map of section_id -> avatar_path
    avatar_map = {}
    for af in avatar_files:
        # Parse section_X_avatar.mp4
        try:
            section_id = int(af.stem.split('_')[1])
            avatar_map[section_id] = af.name
        except (IndexError, ValueError):
            print(f"Skipping unrecognized file: {af.name}")
    
    # Update sections
    updated_count = 0
    for section in pres.get("sections", []):
        sec_id = section.get("section_id")
        if sec_id in avatar_map:
            existing = section.get("avatar_video", "")
            if not existing or existing.strip() == "":
                # Compute relative path for player
                # Player expects: /jobs/{job_id}/avatars/{filename} OR avatars/{filename}
                job_id = job_path.name
                rel_path = f"/jobs/{job_id}/avatars/{avatar_map[sec_id]}"
                section["avatar_video"] = rel_path
                section["avatar_status"] = "completed"
                updated_count += 1
                print(f"  Section {sec_id}: Set avatar_video = {rel_path}")
            else:
                print(f"  Section {sec_id}: Already has avatar_video = {existing}")
    
    if updated_count > 0:
        with open(pres_path, 'w', encoding='utf-8') as f:
            json.dump(pres, f, indent=2)
        print(f"\nUpdated {updated_count} sections in presentation.json")
    else:
        print("\nNo updates needed")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python patch_avatar_paths.py <job_directory>")
        print("Example: python patch_avatar_paths.py player/jobs/4a466399")
        sys.exit(1)
    
    job_dir = sys.argv[1]
    patch_avatar_paths(job_dir)
