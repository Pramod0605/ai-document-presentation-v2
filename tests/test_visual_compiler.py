"""
Unit tests for visual_compiler strict validation.
Tests that vague visual beats are correctly rejected.
"""

import sys
sys.path.insert(0, '.')

from core.visual_compiler import (
    validate_visual_beat_for_compilation,
    compile_wan_prompt,
    compile_manim_plan,
    compile_section_visuals,
    VisualCompilationError,
    VISUAL_INSTRUCTION_MIN_WORDS,
    BANNED_VAGUE_PHRASES
)


def test_rejects_short_instruction():
    """Visual beat with <50 words should be rejected."""
    beat = {
        "visual_instruction": "Show a ball moving left to right with color blue.",
        "labels": ["Ball", "Motion"],
        "motion": "Ball moves from left to right smoothly"
    }
    
    try:
        compile_wan_prompt(beat, section_id=1, beat_index=0)
        print("FAIL: Should have rejected short instruction")
        return False
    except VisualCompilationError as e:
        if "words" in str(e) and "minimum" in str(e):
            print(f"PASS: Rejected short instruction - {e}")
            return True
        print(f"FAIL: Wrong error - {e}")
        return False


def test_rejects_vague_phrases():
    """Visual beat with banned vague phrases should be rejected."""
    long_instruction = (
        "Show clearly the concept of electric field lines radiating outward from a positive charge. "
        "The field lines should demonstrate effectively how the force decreases with distance. "
        "Use blue color for the positive charge at center position. Draw arrows pointing outward "
        "from center to edges of screen. Each arrow has decreasing size as it gets farther from center. "
        "The arrows should be labeled with 'E' for electric field."
    )
    
    beat = {
        "visual_instruction": long_instruction,
        "labels": ["E", "Electric Field"],
        "motion": "Arrows appear one by one from center outward"
    }
    
    try:
        compile_wan_prompt(beat, section_id=1, beat_index=0)
        print("FAIL: Should have rejected vague phrase 'show clearly'")
        return False
    except VisualCompilationError as e:
        if "vague phrases" in str(e).lower():
            print(f"PASS: Rejected vague phrase - {e}")
            return True
        print(f"FAIL: Wrong error type - {e}")
        return False


def test_rejects_missing_labels():
    """Visual beat without labels should be rejected."""
    long_instruction = (
        "A blue circle representing a positive charge sits at the center of the screen. "
        "Red arrows radiate outward from the center in 8 directions (up, down, left, right, diagonals). "
        "Each arrow starts 1cm from center and extends to screen edge. Arrow thickness is 3 pixels. "
        "The arrows animate in sequence, appearing clockwise starting from top arrow. "
        "Background is dark gray color #333333 to provide contrast."
    )
    
    beat = {
        "visual_instruction": long_instruction,
        "labels": [],
        "motion": "Arrows appear one by one clockwise"
    }
    
    try:
        compile_wan_prompt(beat, section_id=1, beat_index=0)
        print("FAIL: Should have rejected missing labels")
        return False
    except VisualCompilationError as e:
        if "label" in str(e).lower():
            print(f"PASS: Rejected missing labels - {e}")
            return True
        print(f"FAIL: Wrong error type - {e}")
        return False


def test_rejects_insufficient_motion():
    """Visual beat with too short motion description should be rejected."""
    long_instruction = (
        "A blue circle representing a positive charge sits at the center of the screen. "
        "Red arrows radiate outward from the center in 8 directions (up, down, left, right, diagonals). "
        "Each arrow starts 1cm from center and extends to screen edge. Arrow thickness is 3 pixels. "
        "Background is dark gray color #333333 to provide contrast with red arrows."
    )
    
    beat = {
        "visual_instruction": long_instruction,
        "labels": ["Positive Charge", "Field Lines"],
        "motion": "fade in"
    }
    
    try:
        compile_wan_prompt(beat, section_id=1, beat_index=0)
        print("FAIL: Should have rejected short motion")
        return False
    except VisualCompilationError as e:
        if "motion" in str(e).lower():
            print(f"PASS: Rejected short motion - {e}")
            return True
        print(f"FAIL: Wrong error type - {e}")
        return False


def test_accepts_valid_beat():
    """A properly detailed visual beat should be accepted."""
    long_instruction = (
        "A bright blue circle with radius 0.5 units sits at screen center position (0, 0). "
        "Eight red arrow vectors radiate outward from the blue circle in 8 directions: up, down, left, right, "
        "and four diagonals at 45-degree angles. Each arrow starts at 1 unit from center and extends to 4 units. "
        "Arrow thickness is 3 pixels with pointed arrowheads. The arrows are labeled with 'E' near their tips. "
        "Background is dark gray #333333 color. Arrow opacity fades from 100% at center to 60% at edges."
    )
    
    beat = {
        "visual_instruction": long_instruction,
        "labels": ["E", "Electric Field", "+q"],
        "motion": "Arrows appear sequentially clockwise starting from top, each taking 0.3 seconds to draw",
        "objects": [
            {"type": "circle", "color": "blue", "label": "+q"},
            {"type": "arrow", "color": "red", "label": "E"}
        ]
    }
    
    try:
        prompt = compile_wan_prompt(beat, section_id=1, beat_index=0)
        print(f"PASS: Accepted valid beat, compiled prompt: {len(prompt)} chars")
        return True
    except VisualCompilationError as e:
        print(f"FAIL: Rejected valid beat - {e}")
        return False


def test_section_compilation_fails_on_vague():
    """compile_section_visuals should return errors for vague beats."""
    section = {
        "id": 3,
        "section_type": "content",
        "renderer": "wan_video",
        "visual_beats": [
            {
                "visual_instruction": "Show the concept beautifully with nice animations.",
                "labels": [],
                "motion": "animate"
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


def print_banned_phrases():
    """Print all banned vague phrases for reference."""
    print(f"\n=== BANNED VAGUE PHRASES ({len(BANNED_VAGUE_PHRASES)}) ===")
    for phrase in BANNED_VAGUE_PHRASES:
        print(f"  - '{phrase}'")
    print(f"\nMinimum word count for visual_instruction: {VISUAL_INSTRUCTION_MIN_WORDS}")


def run_all_tests():
    print("=" * 60)
    print("VISUAL COMPILER STRICT VALIDATION TESTS")
    print("=" * 60)
    
    print_banned_phrases()
    
    print("\n--- Running Tests ---\n")
    
    tests = [
        ("Rejects short instruction (<50 words)", test_rejects_short_instruction),
        ("Rejects vague phrases", test_rejects_vague_phrases),
        ("Rejects missing labels", test_rejects_missing_labels),
        ("Rejects insufficient motion", test_rejects_insufficient_motion),
        ("Accepts valid detailed beat", test_accepts_valid_beat),
        ("Section compilation fails on vague", test_section_compilation_fails_on_vague),
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
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
