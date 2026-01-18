import json
import os

def check_presentation_player_logic(json_path, job_dir):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    missing_files = []
    
    sections = data.get('sections', [])
    for section in sections:
        section_id = section.get('section_id')
        if section_id not in [3, 4, 5, 6]:
            continue
            
        print(f"Checking Section {section_id}...")
        
        # Player Logic for beat_videos in segments:
        # videoPath = `videos/${videoId}.mp4`;
        segments = section.get('narration', {}).get('segments', [])
        for seg in segments:
            for video_id in seg.get('beat_videos', []):
                # Player simulation
                player_path = f"videos/{video_id}.mp4"
                full_path = os.path.join(job_dir, player_path.replace('/', os.sep))
                
                if not os.path.exists(full_path):
                    missing_files.append(f"Section {section_id} Segment {seg.get('segment_id')} FAIL: {player_path} (ID: {video_id})")
                else:
                    print(f"  [OK] {player_path}")

    if missing_files:
        print("\nERRORS FOUND (Player will 404):")
        for msg in missing_files:
            print(f"  - {msg}")
    else:
        print("\nSUCCESS: All segment beat_videos resolved correctly by Player logic.")

if __name__ == "__main__":
    check_presentation_player_logic(
        r'c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\48808436\presentation.json',
        r'c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\48808436'
    )
