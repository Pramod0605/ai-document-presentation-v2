import json
from pathlib import Path

job_id = "d76a0cc1"
pres_path = Path(f"player/jobs/{job_id}/presentation.json")

with open(pres_path, "r", encoding="utf-8") as f:
    data = json.load(f)

sec2 = [s for s in data["sections"] if s["section_id"] == 2][0]

print(f"Section 2: {sec2.get('title')}")
print(f"Renderer: {sec2.get('renderer')}")
print(f"\nSection has these top-level keys:")
for key in sec2.keys():
    print(f"  - {key}")

render_spec = sec2.get("render_spec", {})
print(f"\nrender_spec exists: {bool(render_spec)}")

if render_spec:
    print(f"render_spec keys: {list(render_spec.keys())}")
    
    manim_spec = render_spec.get("manim_scene_spec")
    print(f"\nmanim_scene_spec type: {type(manim_spec)}")
    
    if isinstance(manim_spec, dict):
        print(f"manim_scene_spec dict keys: {list(manim_spec.keys())}")
        if "manim_code" in manim_spec:
            code = manim_spec["manim_code"]
            print(f"\n✅ MANIM CODE FOUND!")
            print(f"Code length: {len(code)} characters")
            print(f"\nFirst 500 chars:\n{code[:500]}")
        else:
            print(f"\n❌ NO 'manim_code' KEY in manim_scene_spec")
            print(f"Available keys: {list(manim_spec.keys())}")
    elif isinstance(manim_spec, str):
        print(f"\nmanim_scene_spec is a STRING (V2.5 prompt style)")
        print(f"Content: {manim_spec[:200]}...")
    else:
        print(f"\n❌ manim_scene_spec is None or unexpected type")
