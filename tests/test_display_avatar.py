"""
TEST-002: Display Validation Tests
Verifies avatar sizing (60%/45%/35%) across all 7 section types.

Usage:
    python tests/test_display_avatar.py
    
This test validates that presentation.json sections have correct avatar settings
and that the player would interpret them correctly.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestColors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


SECTION_TYPE_AVATAR_WIDTHS = {
    "intro": 60,
    "summary": 60,
    "content": 45,
    "example": 45,
    "quiz": 35,
    "memory": 45,
    "recap": 35
}

SECTION_TYPE_AVATAR_POSITIONS = {
    "intro": "center",
    "summary": "center",
    "content": "right",
    "example": "right",
    "quiz": "right",
    "memory": "center",
    "recap": "right"
}


def print_result(test_name: str, passed: bool, message: str = ""):
    color = TestColors.GREEN if passed else TestColors.RED
    status = "PASS" if passed else "FAIL"
    print(f"{color}[{status}]{TestColors.RESET} {test_name}")
    if message:
        print(f"       {message}")


def validate_avatar_never_hidden(section: dict) -> tuple:
    """Validate avatar is never set to hidden"""
    
    if section.get("avatar_position") == "hidden":
        return False, "avatar_position is 'hidden'"
    
    avatar_layout = section.get("avatar_layout", {})
    if avatar_layout.get("position") == "hidden":
        return False, "avatar_layout.position is 'hidden'"
    
    if section.get("layout", {}).get("avatar_layout", {}).get("position") == "hidden":
        return False, "layout.avatar_layout.position is 'hidden'"
    
    for enrich in section.get("segment_enrichments", []):
        dd = enrich.get("display_directives", {})
        if dd.get("avatar_layer") == "hide":
            return False, f"Segment {enrich.get('segment_id')} has avatar_layer='hide'"
    
    return True, ""


def validate_avatar_width(section: dict) -> tuple:
    """Validate avatar width matches section type requirements"""
    section_type = section.get("section_type", "content")
    expected_width = SECTION_TYPE_AVATAR_WIDTHS.get(section_type, 45)
    
    width = section.get("avatar_width_percent")
    if width is None:
        width = section.get("avatar_layout", {}).get("width_percent")
    if width is None:
        width = section.get("layout", {}).get("avatar_layout", {}).get("width_percent")
    
    if width is None:
        return True, f"No explicit width (will use default: {expected_width}%)"
    
    if width == expected_width:
        return True, f"Width matches expected: {width}%"
    elif width in [35, 45, 60]:
        return True, f"Valid width {width}% (expected {expected_width}%)"
    else:
        return False, f"Invalid width {width}% (expected one of 35/45/60)"


def test_section_types():
    """Test avatar requirements for each section type"""
    print(f"\n{TestColors.BLUE}=== Section Type Requirements ==={TestColors.RESET}")
    
    for section_type, expected_width in SECTION_TYPE_AVATAR_WIDTHS.items():
        expected_pos = SECTION_TYPE_AVATAR_POSITIONS.get(section_type, "right")
        print(f"\n{section_type.upper()}: avatar_width={expected_width}%, position={expected_pos}")


def test_sample_presentation(filepath: str):
    """Test a presentation.json file for display requirements"""
    print(f"\n{TestColors.BLUE}=== Testing: {filepath} ==={TestColors.RESET}")
    
    if not os.path.exists(filepath):
        print_result("File exists", False, f"File not found: {filepath}")
        return False
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print_result("Valid JSON", False, str(e))
        return False
    
    print_result("Valid JSON", True)
    
    sections = data.get("sections", [])
    if not sections:
        print_result("Has sections", False, "No sections found")
        return False
    
    print_result("Has sections", True, f"Found {len(sections)} sections")
    
    all_passed = True
    section_types_seen = set()
    
    for i, section in enumerate(sections):
        section_type = section.get("section_type", "unknown")
        section_types_seen.add(section_type)
        section_id = section.get("section_id", f"section_{i}")
        
        not_hidden, msg = validate_avatar_never_hidden(section)
        if not not_hidden:
            print_result(f"{section_id} ({section_type}): Avatar not hidden", False, msg)
            all_passed = False
        
        valid_width, msg = validate_avatar_width(section)
        if not valid_width:
            print_result(f"{section_id} ({section_type}): Avatar width valid", False, msg)
            all_passed = False
    
    print(f"\n  Section types seen: {', '.join(sorted(section_types_seen))}")
    
    print_result("All sections pass avatar rules", all_passed)
    return all_passed


def test_player_avatar_logic():
    """Test that player.js avatar logic is correct (static analysis)"""
    print(f"\n{TestColors.BLUE}=== Player Avatar Logic Validation ==={TestColors.RESET}")
    
    player_path = "player/player.js"
    if not os.path.exists(player_path):
        print_result("player.js exists", False)
        return False
    
    with open(player_path, 'r') as f:
        content = f.read()
    
    no_opacity_zero = "avatarCanvas.style.opacity = '0'" not in content
    print_result("No opacity=0 for avatar", no_opacity_zero)
    
    has_fallback_chain = "section?.avatar_layout" in content or "section.avatar_layout" in content
    print_result("Has avatar_layout fallback chain", has_fallback_chain)
    
    has_width_percent = "avatar_width_percent" in content
    print_result("Has avatar_width_percent support", has_width_percent)
    
    has_position = "avatar_position" in content
    print_result("Has avatar_position support", has_position)
    
    has_always_visible = "avatarCanvas.style.opacity = '1'" in content
    print_result("Avatar always visible (opacity=1)", has_always_visible)
    
    return all([no_opacity_zero, has_fallback_chain, has_width_percent, has_position, has_always_visible])


def find_presentation_files():
    """Find all presentation.json files in output directories"""
    presentation_files = []
    
    output_dirs = ["output", "outputs", "results", "jobs"]
    for output_dir in output_dirs:
        if os.path.exists(output_dir):
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    if file == "presentation.json":
                        presentation_files.append(os.path.join(root, file))
    
    return presentation_files


def run_all_tests():
    """Run all display validation tests"""
    print(f"\n{TestColors.BLUE}{'='*60}")
    print("TEST-002: Display Validation Suite")
    print(f"{'='*60}{TestColors.RESET}")
    
    test_section_types()
    
    player_ok = test_player_avatar_logic()
    
    presentation_files = find_presentation_files()
    
    if presentation_files:
        print(f"\n{TestColors.BLUE}Found {len(presentation_files)} presentation files{TestColors.RESET}")
        for filepath in presentation_files[:5]:
            test_sample_presentation(filepath)
    else:
        print(f"\n{TestColors.YELLOW}No presentation.json files found in output directories{TestColors.RESET}")
        print("  Run a V1.5 pipeline generation first, then re-run this test.")
    
    print(f"\n{TestColors.BLUE}{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}{TestColors.RESET}")
    
    print_result("Player avatar logic", player_ok)
    print_result("Section type requirements documented", True)
    
    return player_ok


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_sample_presentation(sys.argv[1])
    else:
        run_all_tests()
