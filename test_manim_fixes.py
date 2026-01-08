import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from core.agents.manim_code_generator import ManimCodeGenerator

def test_scrubbing():
    print("Testing wait scrubbing...")
    gen = ManimCodeGenerator()
    code = """
        self.play(Write(text))
        self.wait(0.0)
        self.wait( 0 )
        self.wait(0.1)
    """
    cleaned = gen._scrub_invalid_waits(code)
    print(f"Cleaned code:\n{cleaned}")
    assert "self.wait(0.0)" not in cleaned
    assert "self.wait( 0 )" not in cleaned
    assert "self.wait(0.1)" in cleaned
    print("✓ Scrubbing passed!")

def test_enforce_timing():
    print("\nTesting timing enforcement...")
    gen = ManimCodeGenerator()
    section_data = {
        "narration_segments": [
            {"duration": 5.0, "text": "Segment 1"},
            {"duration": 5.0, "text": "Segment 2"}
        ]
    }
    # Initial code with deficit = 0
    code = """
class MainScene(Scene):
    def construct(self):
        # Segment 1
        self.play(Write(Text("1")), run_time=5.0)
        # Segment 2
        self.play(Write(Text("2")), run_time=5.0)
    """
    synced = gen._enforce_timing(code, section_data)
    print(f"Synced code (deficit 0):\n{synced}")
    assert "self.wait(0.0)" not in synced
    
    # Code with positive deficit
    code2 = """
class MainScene(Scene):
    def construct(self):
        # Segment 1
        self.play(Write(Text("1")), run_time=2.0)
        # Segment 2
        self.play(Write(Text("2")), run_time=2.0)
    """
    synced2 = gen._enforce_timing(code2, section_data)
    print(f"Synced code (deficit 3):\n{synced2}")
    assert "self.wait(3.000)" in synced2
    print("✓ Timing enforcement passed!")

if __name__ == "__main__":
    test_scrubbing()
    test_enforce_timing()
