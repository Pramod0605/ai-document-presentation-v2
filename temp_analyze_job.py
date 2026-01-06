
import json
import sys
from pathlib import Path

# Adjust path to your file
json_path = r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\1702aeed\presentation.json"

try:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Loaded JSON. Sections found: {len(data.get('sections', []))}")
    
    sections = data.get('sections', [])
    for i, section in enumerate(sections):
        stype = section.get('section_type', 'unknown')
        renderer = section.get('renderer', 'unknown')
        title = section.get('title', f"Section {i}")
        
        print(f"\n--- Section {i}: {title} [{stype} | {renderer}] ---")
        
        if stype in ["content", "example"]:
            # Check Manim Spec
            if renderer == "manim":
                spec = section.get('manim_scene_spec')
                r_spec = section.get('render_spec', {})
                nested_spec = r_spec.get('manim_scene_spec') if r_spec else None
                
                print(f"  manim_scene_spec (top-level): {str(spec)[:50]}..." if spec else "  manim_scene_spec (top-level): MISSING")
                print(f"  render_spec.manim_scene_spec: {str(nested_spec)[:50]}..." if nested_spec else "  render_spec.manim_scene_spec: MISSING")
                
            # Check Content (Fidelity)
            content = section.get('content')
            print(f"  Content length: {len(content) if content else 0} chars")
            if content:
                print(f"  Content preview: {content[:100]}...")
            else:
                print("  [WARNING] Content is EMPTY!")

        if stype == "recap":
            # Check Video Prompts length
            prompts = section.get('video_prompts', [])
            print(f"  Video Prompts count: {len(prompts)}")
            for j, p in enumerate(prompts):
                p_text = p.get('prompt') if isinstance(p, dict) else str(p)
                w_count = len(p_text.split())
                print(f"    Prompt {j} words: {w_count}")
                if w_count < 80:
                    print(f"    [FAIL] Prompt {j} is too short!")

except Exception as e:
    print(f"Error reading JSON: {e}")
