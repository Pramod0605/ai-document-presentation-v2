import json
import os

def check_presentation(json_path, job_dir):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    missing_files = []
    
    for section in data.get('sections', []):
        section_id = section.get('section_id')
        if section_id not in [3, 4, 5, 6]:
            continue
            
        print(f"Checking Section {section_id}...")
        
        # Check narration segments
        segments = section.get('narration', {}).get('segments', [])
        for seg in segments:
            for video in seg.get('beat_videos', []):
                full_path = os.path.join(job_dir, video.replace('/', os.sep))
                if not os.path.exists(full_path):
                    missing_files.append(f"Section {section_id} Segment {seg.get('segment_id')} missing: {video}")
                else:
                    print(f"  [OK] {video}")
        
        # Check visual_beats
        visual_beats = section.get('visual_beats', [])
        for beat in visual_beats:
            video = beat.get('video_asset')
            if video:
                full_path = os.path.join(job_dir, video.replace('/', os.sep))
                if not os.path.exists(full_path):
                    missing_files.append(f"Section {section_id} Beat {beat.get('beat_id')} missing asset: {video}")
                else:
                    print(f"  [OK] {video}")

    if missing_files:
        print("\nERRORS FOUND:")
        for msg in missing_files:
            print(f"  - {msg}")
    else:
        print("\nAll videos for Sections 3, 4, 5, 6 are PRESENT and linked correctly.")

if __name__ == "__main__":
    check_presentation(
        r'c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\48808436\presentation.json',
        r'c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\48808436'
    )
