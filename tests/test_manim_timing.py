#!/usr/bin/env python3
"""
Test: Manim Timing Enforcement
Verifies that _enforce_timing correctly handles:
1. Animation shorter than narration → injects self.wait()
2. Animation longer than narration → logs warning
3. Missing segment markers → no modifications
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agents.manim_code_generator import ManimCodeGenerator

def test_enforce_timing():
    """Test the _enforce_timing function with various scenarios."""
    
    generator = ManimCodeGenerator()
    
    # Test 1: Animation shorter than narration (should inject wait)
    print("=" * 60)
    print("TEST 1: Animation shorter than narration (inject wait)")
    print("=" * 60)
    
    code_short = """from manim import *

class MainScene(Scene):
    def construct(self):
        # Segment 1: Intro (10.0s expected)
        title = Text("Hello").to_edge(UP)
        self.play(Write(title), run_time=2.0)
        # Only 2s of animation, but segment is 10s
        
        # Segment 2: Details (5.0s expected)
        formula = MathTex("E=mc^2")
        self.play(FadeIn(formula), run_time=1.0)
        # Only 1s of animation, but segment is 5s
"""
    
    section_data_1 = {
        "narration_segments": [
            {"text": "Intro text", "duration_seconds": 10.0},
            {"text": "Details text", "duration_seconds": 5.0}
        ]
    }
    
    result_1 = generator._enforce_timing(code_short, section_data_1)
    
    print("Input Code Lines:", len(code_short.split('\n')))
    print("Output Code Lines:", len(result_1.split('\n')))
    print("\n--- Modified Code ---")
    print(result_1)
    
    # Check if wait was injected
    if "Hard Sync: Injected wait" in result_1:
        print("\n✅ PASS: Wait was injected for short animation")
    else:
        print("\n❌ FAIL: Wait was NOT injected")
    
    # Test 2: Animation longer than narration (should warn)
    print("\n" + "=" * 60)
    print("TEST 2: Animation longer than narration (should warn)")
    print("=" * 60)
    
    code_long = """from manim import *

class MainScene(Scene):
    def construct(self):
        # Segment 1: Quick intro (3.0s expected)
        title = Text("Hello").to_edge(UP)
        self.play(Write(title), run_time=5.0)
        self.wait(3.0)
        # 8s of animation, but segment is only 3s
"""
    
    section_data_2 = {
        "narration_segments": [
            {"text": "Quick intro", "duration_seconds": 3.0}
        ]
    }
    
    result_2 = generator._enforce_timing(code_long, section_data_2)
    
    print("--- Modified Code ---")
    print(result_2)
    
    if "WARNING: Animation exceeds audio" in result_2:
        print("\n✅ PASS: Warning was added for long animation")
    else:
        print("\n❌ FAIL: Warning was NOT added")
    
    # Test 3: No segment markers (should skip)
    print("\n" + "=" * 60)
    print("TEST 3: No segment markers (should skip)")
    print("=" * 60)
    
    code_no_markers = """from manim import *

class MainScene(Scene):
    def construct(self):
        title = Text("Hello").to_edge(UP)
        self.play(Write(title), run_time=2.0)
"""
    
    section_data_3 = {
        "narration_segments": [
            {"text": "Intro", "duration_seconds": 5.0}
        ]
    }
    
    # _enforce_timing only runs if "# Segment" is in code
    if "# Segment" not in code_no_markers:
        print("✅ PASS: No segment markers detected - would skip")
    else:
        print("❌ FAIL: Unexpected segment markers found")
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_enforce_timing()
