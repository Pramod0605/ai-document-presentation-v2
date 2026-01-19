import sys
import os
import logging
from typing import Dict, Any

# Add current directory to path
sys.path.append(os.getcwd())

from core.agents.manim_code_generator import ManimCodeGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_v26_logic():
    generator = ManimCodeGenerator(model="test-model", api_key="test-key")
    
    section_data = {
        "section_title": "Test Section",
        "narration_segments": [
            {"duration": 5.0, "text": "Hello world"},
            {"duration": 10.0, "text": "This is a test"}
        ]
    }
    
    # Sample code WITH timing mismatch and NO FadeOut
    sample_code = """
from manim import *

class MainScene(Scene):
    def construct(self):
        # Segment 1 (5.0s)
        t1 = Text("Hello")
        self.play(Write(t1), run_time=2.0)
        self.wait(1.0) # Total 3.0s, budget 5.0s -> 2s deficit
        
        # Segment 2 (10.0s)
        t2 = Text("Test")
        self.play(FadeIn(t2), run_time=1.0)
        self.wait(5.0) # Total 6.0s, budget 10.0s -> 4s deficit
"""

    print("=== Testing Hard Sync & FadeOut Injection ===")
    synced_code = generator._enforce_timing(sample_code, section_data)
    
    print("\nSynced Code Output:")
    print("-" * 40)
    print(synced_code)
    print("-" * 40)
    
    # Check for FadeOut injection
    assert "FadeOut(*self.mobjects)" in synced_code, "FadeOut injection failed!"
    assert "self.wait(1.5)" in synced_code or "self.wait(1.500)" in synced_code, "Wait injection for Segment 1 failed! (5.0 - 3.0 - 0.5 = 1.5)"
    assert "self.wait(3.5)" in synced_code or "self.wait(3.500)" in synced_code, "Wait injection for Segment 2 failed! (10.0 - 6.0 - 0.5 = 3.5)"
    
    print("\n[PASS] Timing and FadeOut injection verified.")

    print("\n=== Testing Validation Skip ===")
    # This should return NO errors because skip_timing=True, even though the code is intentionally "wrong" for a manual check
    errors = generator.validate_code(synced_code, section_data, skip_timing=True)
    
    print(f"Validation Errors (skip_timing=True): {errors}")
    assert len(errors) == 0, f"Expected no errors when skip_timing=True, got {errors}"
    
    print("\n[PASS] Validation skip verified.")

if __name__ == "__main__":
    try:
        test_v26_logic()
        print("\nALL V2.6 MANIM LOGIC TESTS PASSED!")
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
