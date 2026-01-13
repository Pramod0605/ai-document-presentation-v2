import os
import tempfile
from core.manim_timing_validator import validate_manim_timing

def test_validator():
    print("=== Testing Enhanced Manim Timing Validator ===")
    
    # 1. Test Budget Override (LLM outputs 0s-5s range)
    code_with_range = """
from manim import *
class MainScene(Scene):
    def construct(self):
        # Segment 1 (0.0s - 5.0s)
        self.play(Create(Dot()), run_time=2.0)
        self.wait(3.0)
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as tmp:
        tmp.write(code_with_range)
        path = tmp.name
    
    print("\nTest 1: Budget Override (Expect PASS)")
    # Should pass because external_budgets overrides the regex-picked 0.0s
    try:
        success = validate_manim_timing(path, external_budgets={1: 5.0})
    except RuntimeError as e:
        print(f"FAILED unexpectedly: {e}")
        success = False
    print(f"Result: {'PASS' if success else 'FAIL'}")
    
    # 2. Test Forbidden ASCII (checkmark)
    code_with_check = """
from manim import *
class MainScene(Scene):
    def construct(self):
        # Segment 1 (5.0s)
        t = Text("Done ✓")
        self.play(Write(t), run_time=2.0)
        self.wait(3.0)
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as tmp:
        tmp.write(code_with_check)
        path2 = tmp.name
        
    print("\nTest 2: Forbidden Character (Expect FAIL)")
    try:
        success = validate_manim_timing(path2)
    except RuntimeError as e:
        print(f"Caught expected fatal error: {e}")
        success = False
    print(f"Result: {'FAIL' if not success else 'PASS'}")
    
    # 3. Test Re-assignment (Expect FAIL under New Isolation rules)
    code_with_reassign = """
from manim import *
class MainScene(Scene):
    def construct(self):
        # Segment 1 (5.0s)
        t = Text("A")
        self.play(Write(t), run_time=2.0)
        self.wait(3.0)
        
        # Segment 2 (5.0s)
        # Re-assigning 't' is now a FAIL because PERSISTENCE IS DISABLED
        t = Text("B")
        self.play(Write(t), run_time=2.0)
        self.wait(3.0)
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as tmp:
        tmp.write(code_with_reassign)
        path3 = tmp.name
    print("\nTest 3: Re-assignment (Expect FAIL)")
    try:
        success = validate_manim_timing(path3, external_budgets={1: 5.0, 2: 5.0})
    except RuntimeError as e:
        print(f"Caught expected fatal error: {e}")
        success = False
    print(f"Result: {'FAIL' if not success else 'PASS'}")

    # 4. Test Name Reuse after cleanup (Expect FAIL under New Isolation rules)
    code_with_cleanup = """
from manim import *
class MainScene(Scene):
    def construct(self):
        # Segment 1 (5.0s)
        obj1 = Dot()
        self.play(Create(obj1), run_time=2.0)
        self.wait(3.0)
        
        # Segment 2 (5.0s)
        # Even if obj1 is gone, reusing the name 'obj1' is a FAIL to ensure fresh state
        obj1 = Square()
        self.play(Create(obj1), run_time=2.0)
        self.wait(3.0)
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as tmp:
        tmp.write(code_with_cleanup)
        path4 = tmp.name
    print("\nTest 4: Name Reuse after cleanup (Expect FAIL)")
    try:
        success = validate_manim_timing(path4, external_budgets={1: 5.0, 2: 5.0})
    except RuntimeError as e:
        print(f"Caught expected fatal error: {e}")
        success = False
    print(f"Result: {'FAIL' if not success else 'PASS'}")

    # 5. Test Hard Sync Override (Expect PASS)
    code_with_hardsync = """
from manim import *
class MainScene(Scene):
    def construct(self):
        # Segment 1 (5.0s)
        self.play(Create(Dot()), run_time=6.0) # Intentionally wrong
        self.wait(1.0)
        
        # Segment 2 (5.0s) # Hard Sync
        self.play(Create(Square()))
        self.wait(5.0) # Satisfy pacing
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as tmp:
        tmp.write(code_with_hardsync)
        path5 = tmp.name
    print("\nTest 5: Hard Sync Override (Expect PASS)")
    try:
        success = validate_manim_timing(path5, external_budgets={1: 5.0, 2: 5.0})
    except RuntimeError as e:
        print(f"FAILED unexpectedly: {e}")
        success = False
    print(f"Result: {'PASS' if success else 'FAIL'}")

    # 6. Test Class Name Exclusion (Expect PASS)
    code_with_classes = """
from manim import *
class MainScene(Scene):
    def construct(self):
        # Segment 1 (5.0s)
        t = Text("A")
        self.play(Write(t), run_time=2.0)
        self.wait(3.0)
        
        # Segment 2 (5.0s)
        # Using the CLASS 'Text' should NOT trigger cleanup for 't'
        t2 = Text("B")
        self.play(Write(t2), run_time=2.0)
        self.wait(3.0)
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as tmp:
        tmp.write(code_with_classes)
        path6 = tmp.name
    print("\nTest 6: Class Name Exclusion (Expect PASS)")
    try:
        success = validate_manim_timing(path6, external_budgets={1: 5.0, 2: 5.0})
    except RuntimeError as e:
        print(f"FAILED unexpectedly: {e}")
        success = False
    print(f"Result: {'PASS' if success else 'FAIL'}")

    # Cleanup test files
    for p in [path, path2, path3, path4, path5, path6]:
        if os.path.exists(p):
            os.unlink(p)

def test_wan_logic():
    print("\n--- Running WAN Logic Tests ---")
    # ... rest of wan tests ...
    from core.wan_prompt_validator import expand_short_prompt, truncate_wan_prompt, WAN_GENERIC_EXPANSIONS
    
    # Test 1: Smart Expander (Trust Detailed Prompt)
    # Now trust threshold is 60 words for general, or 40 for technical
    detailed_prompt = "A high-definition scientific visualization showing the intricate process of mitochondrial respiration within a biological cell. The camera zooms into the inner membrane, revealing the complex electron transport chain. Vibrant blue protons move rapidly across the membrane, while orange ATP molecules are synthesized near the ATP synthase enzyme. Professional lighting highlights every detail of the molecular structure. " * 2
    word_count = len(detailed_prompt.split())
    expanded = expand_short_prompt(detailed_prompt)
    print(f"Test WAN 1 (Smart Expander): Detailed prompt {word_count} words. Expanded: {len(expanded.split())} words.")
    assert len(expanded.split()) == word_count, "Detailed prompt should not have been expanded!"

    # Test 2: Smart Expander (Pad Generic)
    generic_prompt = "Cinematic educational visualization."
    expanded = expand_short_prompt(generic_prompt)
    exp_word_count = len(expanded.split())
    print(f"Test WAN 2 (Smart Expander): Generic prompt. Expanded: {exp_word_count} words.")
    # print(f"DEBUG: Expanded content: {expanded}")
    assert exp_word_count >= 80, f"Generic prompt only reached {exp_word_count} words, expected >= 80"

    # Test 3: Surgical Truncation (Remove Filler)
    long_prompt = "CORE CONTENT: " + "X " * 400 + WAN_GENERIC_EXPANSIONS[0]
    truncated = truncate_wan_prompt(long_prompt, max_chars=500)
    print(f"Test WAN 3 (Surgical Truncation): Long prompt {len(long_prompt)} chars. Truncated: {len(truncated)} chars.")
    assert WAN_GENERIC_EXPANSIONS[0] not in truncated, "Surgical truncation should have removed generic filler first!"
    assert "CORE CONTENT" in truncated, "Core content should still be present!"

    print("--- WAN Logic Tests PASSED ---")

if __name__ == "__main__":
    test_validator()
    test_wan_logic()
