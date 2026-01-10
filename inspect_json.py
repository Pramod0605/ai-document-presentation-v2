import json
import os

path = r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\fe78ae5c\presentation.json"

try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sections = data.get("sections", [])
    print(f"Total sections: {len(sections)}")
    
    for i, sec in enumerate(sections[:3]): # Check first 3 sections (Intro, Summary, maybe Content)
        print(f"\n--- Section {i}: {sec.get('section_type')} ---")
        print(f"Title: {sec.get('title')}")
        print(f"Audio Path: {sec.get('audio_path')}")
        print(f"Avatar Video: {sec.get('avatar_video')}")
        
        vc = sec.get("visual_content", {})
        print(f"Visual Content Keys: {list(vc.keys())}")
        if "bullet_points" in vc:
            print(f"Bullet Points: {vc['bullet_points']}")
            
        vb = sec.get("visual_beats", [])
        print(f"Visual Beats Count: {len(vb)}")
        if vb:
           print(f"Beat 0: {vb[0]}")

        narration = sec.get("narration", {})
        segments = narration.get("segments", [])
        print(f"Segments Count: {len(segments)}")
        if segments:
            for s_idx, s in enumerate(segments):
                print(f"Seg {s_idx} VC: {s.get('visual_content')}")

except Exception as e:
    print(f"Error: {e}")
