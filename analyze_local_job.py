import json

def analyze_presentation(json_file):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except UnicodeDecodeError:
        with open(json_file, 'r', encoding='utf-16') as f:
            data = json.load(f)

    print(f"Job Title: {data.get('title')}")
    print("-" * 30)
    for section in data.get('sections', []):
        sid = section.get('section_id')
        renderer = section.get('renderer')
        vpath = section.get('video_path')
        if renderer == 'manim':
            print(f"Section {sid}: Renderer={renderer}, VideoPath={vpath}")

if __name__ == "__main__":
    analyze_presentation('local_job_aa400742_presentation.json')
