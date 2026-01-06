import json
from pathlib import Path

# Path to presentation.json
path = Path(r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\603bd693\presentation.json")

if not path.exists():
    print("File not found!")
else:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    sections = data.get("sections", [])
    # Find Section 5
    sec5 = next((s for s in sections if s.get("section_id") == 5 or s.get("id") == 5), None)
    
    if sec5:
        print(f"\n[SECTION 5 ANALYSIS]")
        print(f"Renderer: {sec5.get('renderer')}")
        print(f"Video Path: {sec5.get('video_path')}")
        print(f"Content Video Path: {sec5.get('content_video_path')}")
        
        segments = sec5.get("narration", {}).get("segments", [])
        for i, seg in enumerate(segments):
            directives = seg.get("display_directives", {})
            print(f"Segment {i}: Text={directives.get('text_layer')}, Visual={directives.get('visual_layer')}")
    else:
        print("Section 5 not found.")
