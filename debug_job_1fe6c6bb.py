import json
import os

path = r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\1fe6c6bb\presentation.json"

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for s in data['sections']:
    print(f"ID: {s.get('section_id')} | Type: {s.get('section_type')} | Renderer: {s.get('renderer')}")
    if s.get('section_id') in ['3', 3]:
        print(f"--- Section {s.get('section_id')} Segments ---")
        segs = s.get('narration', {}).get('segments', [])
        for i, seg in enumerate(segs):
             print(f"  Seg {i}: {seg.get('display_directives')}")
