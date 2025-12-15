"""
Unit tests for visual_compiler strict validation.
Tests that incomplete visual beats are correctly rejected.

NEW SCHEMA: Each visual beat must have 5 required fields:
- scene_setup
- objects_and_properties
- motion_sequence
- labels_and_text
- pedagogical_focus
"""

import sys
sys.path.insert(0, '.')

from core.visual_compiler import (
    validate_visual_beat_structure,
    compile_wan_prompt,
    compile_manim_plan,
    compile_section_visuals,
    VisualCompilationError,
    REQUIRED_VISUAL_BEAT_FIELDS,
    BANNED_VAGUE_PHRASES,
    MIN_FIELD_WORDS
)


def make_valid_beat():
    """Create a valid visual beat with all 5 required fields."""
    return {
        "segment_id": 1,
        "scene_setup": "A white background with a 2D Cartesian coordinate system. X-axis from -5 to 5, Y-axis from -5 to 5. Grid lines visible in light gray.",
        "objects_and_properties": "A blue circle with radius 2 units at position (0,0). A red arrow 4 units long starting at (0,0) pointing to (3,2). A green label text at position (3.5, 2.5).",
        "motion_sequence": "First, the coordinate axes fade in. Then, the blue circle appears at origin. Next, the red arrow grows from origin to endpoint. Finally, the label fades in.",
        "labels_and_text": "Label 'O' at origin (0,0). Label 'F=5N' above the red arrow tip at (3.2, 2.2). Label 'Force Vector' in the corner.",
        "pedagogical_focus": "Students should understand that force is a vector with both magnitude and direction, represented by arrows in physics diagrams."
    }


def test_rejects_missing_fields():
    """Visual beat missing required fields should be rejected."""
    beat = {
        "segment_id": 1,
        "scene_setup": "A white background with coordinate system visible. Grid lines at every unit.",
    }
    
    try:
        compile_wan_prompt(beat, section_id=1, beat_index=0)
        print("FAIL: Should have rejected missing fields")
        return False
    except VisualCompilationError as e:
        if "missing required fields" in str(e).lower():
            print(f"PASS: Rejected missing fields - {e}")
            return True
        print(f"FAIL: Wrong error - {e}")
        return False


def test_rejects_short_fields():
    """Visual beat with too-short fields should be rejected."""
    beat = {
        "segment_id": 1,
        "scene_setup": "White background only.",
        "objects_and_properties": "A red arrow.",
        "motion_sequence": "Arrow appears.",
        "labels_and_text": "Label F.",
        "pedagogical_focus": "Force concept."
    }
    
    try:
        compile_wan_prompt(beat, section_id=1, beat_index=0)
        print("FAIL: Should have rejected short fields")
        return False
    except VisualCompilationError as e:
        if "too short" in str(e).lower() or "words" in str(e).lower():
            print(f"PASS: Rejected short fields - {e}")
            return True
        print(f"FAIL: Wrong error - {e}")
        return False


def test_rejects_vague_phrases():
    """Visual beat with banned vague phrases should be rejected."""
    beat = make_valid_beat()
    beat["objects_and_properties"] = (
        "Show clearly the electric field lines radiating outward from the positive charge. "
        "The field lines should demonstrate effectively how the force decreases with distance. "
        "Use appropriate colors for the visualization that illustrate the concept well."
    )
    
    try:
        compile_wan_prompt(beat, section_id=1, beat_index=0)
        print("FAIL: Should have rejected vague phrase 'show clearly'")
        return False
    except VisualCompilationError as e:
        if "vague" in str(e).lower():
            print(f"PASS: Rejected vague phrase - {e}")
            return True
        print(f"FAIL: Wrong error type - {e}")
        return False


def test_accepts_valid_beat():
    """A properly structured visual beat should be accepted."""
    beat = make_valid_beat()
    
    try:
        prompt = compile_wan_prompt(beat, section_id=1, beat_index=0)
        print(f"PASS: Accepted valid beat, compiled prompt: {len(prompt)} chars")
        return True
    except VisualCompilationError as e:
        print(f"FAIL: Rejected valid beat - {e}")
        return False


def test_section_compilation_fails_on_incomplete():
    """compile_section_visuals should return errors for incomplete beats."""
    section = {
        "id": 3,
        "section_type": "content",
        "renderer": "wan_video",
        "visual_beats": [
            {
                "segment_id": 1,
                "scene_setup": "Background only."
            }
        ]
    }
    
    wan_prompt, manim_plan, errors = compile_section_visuals(section)
    
    if errors and len(errors) > 0:
        print(f"PASS: Section compilation returned {len(errors)} errors: {errors[0]}")
        return True
    else:
        print("FAIL: Section compilation should have returned errors")
        return False


def test_manim_compilation():
    """Test that Manim plans are compiled correctly from structured beats."""
    beat = make_valid_beat()
    
    try:
        plan = compile_manim_plan(beat, section_id=1, beat_index=0)
        if "scene_type" in plan and "params" in plan and "structured_fields" in plan:
            print(f"PASS: Manim plan compiled with scene_type: {plan['scene_type']}, params: {list(plan['params'].keys())}")
            return True
        print(f"FAIL: Manim plan missing expected fields. Got: {list(plan.keys())}")
        return False
    except VisualCompilationError as e:
        print(f"FAIL: Rejected valid beat for Manim - {e}")
        return False


def print_schema_info():
    """Print schema information for reference."""
    print(f"\n=== VISUAL BEAT SCHEMA ===")
    print(f"Required fields: {REQUIRED_VISUAL_BEAT_FIELDS}")
    print(f"Minimum words per field: {MIN_FIELD_WORDS}")
    print(f"\n=== BANNED VAGUE PHRASES ({len(BANNED_VAGUE_PHRASES)}) ===")
    for phrase in BANNED_VAGUE_PHRASES[:5]:
        print(f"  - '{phrase}'")
    print(f"  ... and {len(BANNED_VAGUE_PHRASES) - 5} more")


def run_all_tests():
    print("=" * 60)
    print("VISUAL COMPILER STRUCTURED VALIDATION TESTS")
    print("=" * 60)
    
    print_schema_info()
    
    print("\n--- Running Tests ---\n")
    
    tests = [
        ("Rejects missing fields", test_rejects_missing_fields),
        ("Rejects short fields", test_rejects_short_fields),
        ("Rejects vague phrases", test_rejects_vague_phrases),
        ("Accepts valid structured beat", test_accepts_valid_beat),
        ("Section compilation fails on incomplete", test_section_compilation_fails_on_incomplete),
        ("Manim compilation works", test_manim_compilation),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        print(f"\nTest: {name}")
        try:
            if test_fn():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
