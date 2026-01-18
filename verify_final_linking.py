import json
import os

def check_presentation_complete_player_logic(json_path, job_dir):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    errors = []
    
    sections = data.get('sections', [])
    for section in sections:
        section_id = section.get('section_id')
        if section_id not in [3, 4, 5, 6]:
            continue
            
        print(f"Checking Section {section_id}...")
        
        # 1. Segments (beat_videos)
        segments = section.get('narration', {}).get('segments', [])
        for seg in segments:
            for video_id in seg.get('beat_videos', []):
                # Simulated Idempotent Player Logic
                clean_id = video_id
                if clean_id.startswith('videos/'): clean_id = clean_id[7:]
                if clean_id.endswith('.mp4'): clean_id = clean_id[:-4]
                player_path = f"videos/{clean_id}.mp4"
                
                full_path = os.path.join(job_dir, player_path.replace('/', os.sep))
                
                if not os.path.exists(full_path):
                    errors.append(f"Section {section_id} Segment {seg.get('segment_id')} BeatVideo FAIL: {player_path} (ID: {video_id})")
                else:
                    print(f"  [OK] Segment Beat: {player_path}")

        # 2. Visual Beats (video_asset)
        visual_beats = section.get('visual_beats', [])
        for beat in visual_beats:
            video_asset = beat.get('video_asset')
            if video_asset:
                # Player logic: contentVideo.src = resolveMediaPath(videoPath, 'video');
                # resolveMediaPath(path, 'video') adds 'videos/' if not present, and prepends BASE_PATH
                path = video_asset
                
                # Resolve manual simulation
                if not (path.startswith('/jobs/') or path.startswith('/player/jobs/') or path.startswith('http')):
                    if not ('avatars/' in path or 'videos/' in path or 'audio/' in path or 'images/' in path):
                        path = 'videos/' + path
                
                full_path = os.path.join(job_dir, path.replace('/', os.sep))
                
                if not os.path.exists(full_path):
                    errors.append(f"Section {section_id} VisualBeat Asset FAIL: {path} (Asset: {video_asset})")
                else:
                    print(f"  [OK] Visual Asset: {path}")

    if errors:
        print("\nERRORS FOUND:")
        for msg in errors:
            print(f"  - {msg}")
    else:
        print("\nSUCCESS: All videos in Sections 3-6 are correctly linked for Player V2.5.")

if __name__ == "__main__":
    check_presentation_complete_player_logic(
        r'c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\48808436\presentation.json',
        r'c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\48808436'
    )
