import json

def list_manim_sections(json_file):
    encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1']
    for enc in encodings:
        try:
            with open(json_file, 'r', encoding=enc) as f:
                data = json.load(f)
            print(f"--- Loaded with {enc} ---")
            for section in data.get('sections', []):
                sid = section.get('section_id')
                renderer = section.get('renderer')
                vpath = section.get('video_path', 'None')
                if renderer == 'manim':
                    print(f"Section {sid}: {renderer} -> {vpath}")
            return
        except Exception:
            continue
    print("Failed to load JSON")

if __name__ == "__main__":
    list_manim_sections('job_02436e7c_presentation.json')
