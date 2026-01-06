import json

p = json.load(open('player/jobs/d76a0cc1/presentation.json', encoding='utf-8'))
s = [x for x in p['sections'] if x['section_id'] == 2][0]

print(f"Section 2: {s.get('title')}")
print(f"Renderer: {s.get('renderer')}")

nar = s.get('narration', {})
print(f"\n=== NARRATION DATA ===")
print(f"Full text length: {len(nar.get('full_text', 'NO TEXT'))} chars")
print(f"Full text preview: {nar.get('full_text', 'NO TEXT')[:200]}...")

segments = nar.get('segments', [])
print(f"\nNumber of segments: {len(segments)}")

if segments:
    print(f"\n=== FIRST SEGMENT ===")
    seg = segments[0]
    print(f"Keys: {list(seg.keys())}")
    for key, val in seg.items():
        if isinstance(val, str) and len(val) > 100:
            print(f"{key}: {val[:100]}...")
        else:
            print(f"{key}: {val}")
            
print(f"\n=== RENDER_SPEC ===")
rs = s.get('render_spec', {})
mss = rs.get('manim_scene_spec', {})
print(f"manim_scene_spec type: {type(mss)}")
if isinstance(mss, dict):
    print(f"Keys: {list(mss.keys())}")
    if 'description' in mss:
        print(f"Description: {mss['description'][:200] if isinstance(mss['description'], str) else mss['description']}...")
