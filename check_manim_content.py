import json

def check_manim_content(json_file):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        with open(json_file, 'r', encoding='utf-16') as f:
            data = json.load(f)

    for section in data.get('sections', []):
        if section.get('renderer') == 'manim':
            sid = section.get('section_id')
            m_code = section.get('manim_code')
            m_spec = section.get('manim_spec')
            print(f"Section {sid}: manim_code length={len(m_code) if m_code else 0}, manim_spec present={'Yes' if m_spec else 'No'}")

if __name__ == "__main__":
    check_manim_content('local_job_aa400742_presentation.json')
