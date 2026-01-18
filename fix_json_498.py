import json
import os

job_id = '498d0d5a'
base_dir = f'player/jobs/{job_id}'
json_path = f'{base_dir}/presentation.json'
avatars_dir = f'{base_dir}/avatars'

print(f'Checking {avatars_dir}...')
if os.path.exists(avatars_dir):
    files = sorted(os.listdir(avatars_dir))
    print('Avatar files found:', files)
else:
    print('Avatars dir NOT FOUND')
    files = []

print(f'\nReading {json_path}...')
try:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception as e:
    print(f"Error reading JSON: {e}")
    exit(1)

print('\n--- CURRENT STATE ---')
sections = data.get('sections', [])
for s in sections:
    sid = s.get("section_id")
    current_val = s.get("avatar_video", "MISSING")
    print(f'Section {sid}: {current_val}')

print('\n--- APPLYING FIX ---')
updated = False
for s in sections:
    sid = s.get('section_id')
    stype = s.get('section_type')
    
    # Expected filename: section_{id}_avatar.mp4
    expected_file = f'section_{sid}_avatar.mp4'
    
    if expected_file in files:
        # Correct relative path
        correct_path = f'avatars/{expected_file}'
        
        current_path = s.get('avatar_video')
        
        # Normalize for comparison (handle potential None)
        if current_path != correct_path:
            print(f'Updating Section {sid}: {current_path!r} -> {correct_path!r}')
            s['avatar_video'] = correct_path
            s['avatar_status'] = 'completed'
            updated = True
        else:
             print(f'Section {sid} is already correct.')
    else:
        # Check if recap (usually skips avatar)
        if stype == 'recap':
            print(f'Skipping Section {sid} (recap) - no avatar expected.')
        else:
             print(f'WARNING: Could not find avatar file {expected_file} for Section {sid}')

if updated:
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print('\nSuccessfully saved presentation.json')
else:
    print('\nNo changes needed.')
