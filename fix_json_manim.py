import json
import re

def fix_manim_code(code):
    if not code:
        return code
    
    # Fix Polygon.edges/triangle.edges error
    # Instead of .get_edges()[i], we should use side_lines[i] for Square or lines between vertices for Polygon
    # But usually .get_edges() might work if it exists. 
    # Actually, in Manim v0.18+, VMobject doesn't have .edges.
    # We can replace .get_edges()[i] with Line(self.get_vertices()[i], self.get_vertices()[(i+1)%len(self.get_vertices())]) if we are in a subclass
    # But for now, let's try a simple replacement that is common in these LLM outputs:
    # .get_edges() -> .get_lines() or similar? 
    # Actually, let's just create the line explicitly if we know it's a triangle.
    
    # Most common error: .get_edges()
    # Let's replace it with a manual vertex line
    def replace_edge(match):
        obj = match.group(1)
        idx = int(match.group(2))
        return f"Line({obj}.get_vertices()[{idx}], {obj}.get_vertices()[({idx}+1)%len({obj}.get_vertices())])"

    # Match obj.get_edges()[idx]
    code = re.sub(r'(\w+)\.get_edges()\[(\d+)\]', replace_edge, code)
    
    # Fix ShowCreation -> Create
    code = code.replace("ShowCreation", "Create")
    
    return code

def process_json(input_file, output_file):
    try:
        with open(input_file, 'r', encoding='utf-16') as f:
            data = json.load(f)
    except:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

    for section in data.get('sections', []):
        # Fix in render_spec
        rs = section.get('render_spec', {})
        mss = rs.get('manim_scene_spec', {})
        if 'manim_code' in mss:
            mss['manim_code'] = fix_manim_code(mss['manim_code'])
        
        # Fix in explanation_plan
        ep = section.get('explanation_plan', {})
        if 'v15_manim_code' in ep:
            ep['v15_manim_code'] = fix_manim_code(ep['v15_manim_code'])
            
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    process_json('local_job_aa400742_presentation.json', 'fixed_job_aa400742_presentation.json')
