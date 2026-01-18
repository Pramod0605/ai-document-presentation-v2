
import json
import os
import re
import argparse
from pathlib import Path
import datetime

def fix_beat_ids(presentation: dict) -> int:
    """
    Fixes topic_section_1_ prefix in WAN sections to use correct section_id.
    """
    fixed_count = 0
    sections = presentation.get("sections", [])
    
    for section in sections:
        sid = section.get("section_id")
        renderer = section.get("renderer", "").lower()
        
        # Only target WAN sections (renderer 'video' or 'wan')
        if renderer not in ["video", "wan"]:
            continue
            
        correct_prefix = f"topic_section_{sid}"
        
        # 1. Fix video_prompts
        if "video_prompts" in section:
            for prompt in section["video_prompts"]:
                old_id = prompt.get("beat_id", "")
                if "topic_section_1_" in old_id and sid != 1:
                    new_id = old_id.replace("topic_section_1_", f"{correct_prefix}_")
                    prompt["beat_id"] = new_id
                    fixed_count += 1
                    
        # 2. Fix narration segments beat_videos
        if "narration" in section and "segments" in section["narration"]:
            for seg in section["narration"]["segments"]:
                if "beat_videos" in seg:
                    new_beats = []
                    for beat in seg["beat_videos"]:
                        if "topic_section_1_" in beat and sid != 1:
                            new_beats.append(beat.replace("topic_section_1_", f"{correct_prefix}_"))
                            fixed_count += 1
                        else:
                            new_beats.append(beat)
                    seg["beat_videos"] = new_beats
                    
        # 3. Fix render_spec segment_specs beats
        if "render_spec" in section and "segment_specs" in section["render_spec"]:
            for spec in section["render_spec"]["segment_specs"]:
                if "beats" in spec:
                    for beat in spec["beats"]:
                        old_id = beat.get("beat_id", "")
                        if "topic_section_1_" in old_id and sid != 1:
                            beat["beat_id"] = old_id.replace("topic_section_1_", f"{correct_prefix}_")
                            fixed_count += 1
                            
    return fixed_count

def main():
    parser = argparse.ArgumentParser(description="Fix WAN beat IDs in presentation.json")
    parser.add_argument("--job-id", required=True, help="Job ID to fix")
    args = parser.parse_args()
    
    base_dir = Path(r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation")
    job_dir = base_dir / "player" / "jobs" / args.job_id
    json_path = job_dir / "presentation.json"
    
    if not json_path.exists():
        print(f"ERROR: {json_path} not found")
        return
        
    # Create backup
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = json_path.with_suffix(f".json.bak_{timestamp}")
    import shutil
    shutil.copy2(json_path, backup_path)
    print(f"Backup created: {backup_path}")
    
    with open(json_path, "r", encoding="utf-8") as f:
        presentation = json.load(f)
        
    fixed = fix_beat_ids(presentation)
    
    if fixed > 0:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(presentation, f, indent=2)
        print(f"SUCCESS: Fixed {fixed} beat ID references in {json_path}")
    else:
        print("No incorrect beat IDs found.")

if __name__ == "__main__":
    main()
