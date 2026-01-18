import json

p = json.load(open('player/jobs/462e6496/presentation.json', 'r', encoding='utf-8'))
for s in p['sections']:
    if s.get('renderer') == 'manim':
        print(f"Section {s['section_id']}:")
        print(f"  renderer: {s.get('renderer')}")
        print(f"  section_type: {s.get('section_type')}")        
        rs = s.get('render_spec', {})
        mss = rs.get('manim_scene_spec', {})
        if isinstance(mss, dict):
            print(f"  has manim_code: {bool(mss.get('manim_code'))}")
            if mss.get('manim_code'):
                print(f"  code_length: {len(mss.get('manim_code', ''))}")
        print(f"  render_error: {s.get('render_error', 'NONE')}")
        print()
