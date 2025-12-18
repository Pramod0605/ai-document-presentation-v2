#!/usr/bin/env python3
"""
Isolated Manim-only test script.

This script tests the Manim rendering pipeline without:
- PDF conversion (Datalab)
- WAN video generation (Kie.ai)
- TTS generation (Narakeet)

It directly reads markdown, sends to LLM Director, and renders Manim videos.
Use this to validate synchronized LaTeX animations work correctly.

Usage:
    python scripts/test_manim_only.py test_content/math_test.md --dry-run
    python scripts/test_manim_only.py test_content/math_test.md --render
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm_client import generate_chunked_presentation, load_system_prompt, load_user_prompt
from core.visual_compiler import compile_section_visuals, translate_spec_to_manim_code
from render.manim.manim_runner import render_manim_video


def test_visual_compiler_only():
    """Test the visual compiler with a sample manim_scene_spec."""
    print("\n" + "=" * 60)
    print("TEST 1: Visual Compiler - Synchronized LaTeX Animation")
    print("=" * 60)
    
    sample_spec = {
        "objects": [],
        "equations": [
            {
                "id": "quadratic",
                "latex": "x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}",
                "position": "center",
                "animation_style": "element_reveal",
                "reveal_steps": [
                    {"reveal": "x", "at_time": 0.0},
                    {"reveal": "=", "at_time": 0.3},
                    {"reveal": "\\frac{-b", "at_time": 0.6},
                    {"reveal": "\\pm", "at_time": 1.0},
                    {"reveal": "\\sqrt{b^2-4ac}", "at_time": 1.5},
                    {"reveal": "}{2a}", "at_time": 2.5}
                ]
            }
        ],
        "animation_sequence": [
            {"action": "show_equation", "target": "quadratic", "duration": 4.0, "style": "element_reveal"}
        ]
    }
    
    print("\nInput spec:")
    print(json.dumps(sample_spec, indent=2))
    
    try:
        manim_code = translate_spec_to_manim_code(sample_spec, section_id=1, beat_index=0)
        print("\nGenerated Manim code:")
        print("-" * 40)
        print(manim_code)
        print("-" * 40)
        print("\n[OK] Visual compiler generated code successfully")
        return True
    except Exception as e:
        print(f"\n[FAIL] Visual compiler error: {e}")
        return False


def test_geometry_shapes():
    """Test geometry shape generation (Pythagorean theorem)."""
    print("\n" + "=" * 60)
    print("TEST 2: Visual Compiler - Geometry Shapes")
    print("=" * 60)
    
    sample_spec = {
        "objects": [
            {"id": "triangle", "type": "polygon", "vertices": [[0,0], [3,0], [3,4]], "properties": {"color": "blue"}},
            {"id": "square_a", "type": "square", "position": [-2, 0], "properties": {"side": 1.5, "color": "red", "label": "a²"}},
            {"id": "square_b", "type": "square", "position": [5, 0], "properties": {"side": 2, "color": "green", "label": "b²"}}
        ],
        "equations": [
            {"id": "pythagorean", "latex": "a^2 + b^2 = c^2", "position": "top_center"}
        ],
        "animation_sequence": [
            {"action": "draw", "target": "triangle", "duration": 1.0},
            {"action": "grow", "target": "square_a", "duration": 0.8},
            {"action": "grow", "target": "square_b", "duration": 0.8},
            {"action": "show_equation", "target": "pythagorean", "duration": 1.5}
        ]
    }
    
    print("\nInput spec:")
    print(json.dumps(sample_spec, indent=2))
    
    try:
        manim_code = translate_spec_to_manim_code(sample_spec, section_id=2, beat_index=0)
        print("\nGenerated Manim code:")
        print("-" * 40)
        print(manim_code)
        print("-" * 40)
        print("\n[OK] Geometry shapes generated successfully")
        return True
    except Exception as e:
        print(f"\n[FAIL] Geometry generation error: {e}")
        return False


def test_calculus_graph():
    """Test calculus graph with derivative."""
    print("\n" + "=" * 60)
    print("TEST 3: Visual Compiler - Calculus Graph")
    print("=" * 60)
    
    sample_spec = {
        "objects": [
            {"id": "axes", "type": "axes", "position": [0, 0], "properties": {"x_range": [-2, 4, 1], "y_range": [-1, 10, 2]}},
            {"id": "curve", "type": "graph", "properties": {"equation": "x**2", "color": "blue", "axes": "axes"}},
            {"id": "tangent_point", "type": "point", "position": [2, 4], "properties": {"color": "yellow", "label": "P(2,4)"}}
        ],
        "equations": [
            {"id": "derivative", "latex": "\\frac{d}{dx}(x^2) = 2x", "position": "top_center"}
        ],
        "animation_sequence": [
            {"action": "draw", "target": "axes", "duration": 1.0},
            {"action": "draw", "target": "curve", "duration": 1.5},
            {"action": "appear", "target": "tangent_point", "duration": 0.5},
            {"action": "show_equation", "target": "derivative", "duration": 1.5}
        ]
    }
    
    print("\nInput spec:")
    print(json.dumps(sample_spec, indent=2))
    
    try:
        manim_code = translate_spec_to_manim_code(sample_spec, section_id=3, beat_index=0)
        print("\nGenerated Manim code:")
        print("-" * 40)
        print(manim_code)
        print("-" * 40)
        print("\n[OK] Calculus graph generated successfully")
        return True
    except Exception as e:
        print(f"\n[FAIL] Calculus graph error: {e}")
        return False


def test_llm_director(markdown_path: str, subject: str = "Mathematics", grade: str = "10"):
    """Test LLM Director with math content."""
    print("\n" + "=" * 60)
    print("TEST 4: LLM Director - Math Content Generation")
    print("=" * 60)
    
    if not os.path.exists(markdown_path):
        print(f"[FAIL] File not found: {markdown_path}")
        return None
    
    with open(markdown_path, 'r') as f:
        markdown_content = f.read()
    
    print(f"\nProcessing: {markdown_path}")
    print(f"Content length: {len(markdown_content)} chars")
    
    try:
        presentation, trace = generate_chunked_presentation(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade
        )
        
        print(f"\n[OK] LLM Director generated presentation")
        print(f"  - Sections: {len(presentation.get('sections', []))}")
        
        manim_sections = [s for s in presentation.get('sections', []) if s.get('renderer') == 'manim']
        print(f"  - Manim sections: {len(manim_sections)}")
        
        for section in manim_sections:
            print(f"\n  Section {section.get('id')}: {section.get('title')}")
            visual_beats = section.get('visual_beats', [])
            print(f"    Visual beats: {len(visual_beats)}")
            for i, beat in enumerate(visual_beats):
                has_spec = 'manim_scene_spec' in beat
                print(f"      Beat {i}: manim_scene_spec={'YES' if has_spec else 'NO'}")
                if has_spec:
                    spec = beat['manim_scene_spec']
                    print(f"        - objects: {len(spec.get('objects', []))}")
                    print(f"        - equations: {len(spec.get('equations', []))}")
                    print(f"        - animation_sequence: {len(spec.get('animation_sequence', []))}")
        
        return presentation
        
    except Exception as e:
        print(f"\n[FAIL] LLM Director error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_manim_render(presentation: dict, output_dir: str, dry_run: bool = True):
    """Test Manim rendering of generated presentation."""
    print("\n" + "=" * 60)
    print(f"TEST 5: Manim Rendering {'(DRY RUN)' if dry_run else '(ACTUAL)'}")
    print("=" * 60)
    
    os.makedirs(output_dir, exist_ok=True)
    
    manim_sections = [s for s in presentation.get('sections', []) if s.get('renderer') == 'manim']
    
    if not manim_sections:
        print("[SKIP] No Manim sections to render")
        return True
    
    success_count = 0
    fail_count = 0
    
    for section in manim_sections:
        section_id = section.get('id')
        title = section.get('title', 'Untitled')
        print(f"\n  Rendering section {section_id}: {title}")
        
        try:
            video_path = render_manim_video(
                topic=section,
                output_dir=output_dir,
                dry_run=dry_run
            )
            print(f"    [OK] Output: {video_path}")
            success_count += 1
        except Exception as e:
            print(f"    [FAIL] {e}")
            fail_count += 1
    
    print(f"\n  Results: {success_count} success, {fail_count} failed")
    return fail_count == 0


def main():
    parser = argparse.ArgumentParser(description='Test Manim rendering pipeline in isolation')
    parser.add_argument('markdown_file', nargs='?', default='test_content/math_test.md',
                        help='Path to markdown file (default: test_content/math_test.md)')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Generate code but skip actual Manim rendering (default)')
    parser.add_argument('--render', action='store_true',
                        help='Actually render Manim videos')
    parser.add_argument('--compiler-only', action='store_true',
                        help='Only test visual compiler, skip LLM')
    parser.add_argument('--subject', default='Mathematics',
                        help='Subject for LLM prompt (default: Mathematics)')
    parser.add_argument('--grade', default='10',
                        help='Grade level for LLM prompt (default: 10)')
    parser.add_argument('--output-dir', default='test_output/manim_test',
                        help='Output directory for rendered videos')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("MANIM-ONLY TEST SUITE")
    print("=" * 60)
    
    results = []
    
    results.append(("Visual Compiler - Synchronized LaTeX", test_visual_compiler_only()))
    results.append(("Visual Compiler - Geometry Shapes", test_geometry_shapes()))
    results.append(("Visual Compiler - Calculus Graph", test_calculus_graph()))
    
    if not args.compiler_only:
        presentation = test_llm_director(
            args.markdown_file,
            subject=args.subject,
            grade=args.grade
        )
        
        if presentation:
            results.append(("LLM Director", True))
            
            output_path = Path(args.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            with open(output_path / "presentation.json", "w") as f:
                json.dump(presentation, f, indent=2)
            print(f"\n[SAVED] Presentation: {output_path / 'presentation.json'}")
            
            dry_run = not args.render
            render_success = test_manim_render(presentation, str(output_path), dry_run=dry_run)
            results.append(("Manim Rendering", render_success))
        else:
            results.append(("LLM Director", False))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
