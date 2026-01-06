"""
Unit Test: Manim Rendering (v0.19.0)

Tests that Manim v0.19.0 can render a minimal test scene.
"""
import subprocess
import tempfile
from pathlib import Path
import sys

def test_manim_render():
    """Test Manim v0.19.0 rendering with minimal code."""
    print("=" * 60)
    print("TEST: Manim v0.19.0 Rendering")
    print("=" * 60)
    
    # Minimal test code
    test_code = """from manim import *

class TestScene(Scene):
    def construct(self):
        # Minimal animation
        axes = Axes(x_range=[-3, 3], y_range=[0, 10])
        curve = axes.plot(lambda x: x**2, color=YELLOW)
        title = Text("Test").to_edge(UP)
        
        self.play(Create(axes), FadeIn(title), run_time=2)
        self.play(Create(curve), run_time=2)
        self.wait(1)
"""
    
    print(f"✓ Test code prepared ({len(test_code)} chars)")
    
    # Write to temp file
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_file = f.name
            f.write(test_code)
        
        print(f"✓ Temp file created: {temp_file}")
        
        # Run Manim
        print(f"\n⏳ Running Manim render...")
        result = subprocess.run([
            "manim", "render", temp_file, "TestScene",
            "-ql",  # Low quality for speed
            "--format", "mp4",
            "--disable_caching"
        ], capture_output=True, text=True, timeout=60)
        
        print(f"\n📊 Manim Execution:")
        print(f"  Return code: {result.returncode}")
        print(f"  STDOUT length: {len(result.stdout)} chars")
        print(f"  STDERR length: {len(result.stderr)} chars")
        
        # Check output
        if result.returncode == 0:
            print(f"\n✅ Manim render SUCCESSFUL")
            
            # Try to find output file
            output_dir = Path(temp_file).parent / "media" / "videos" / Path(temp_file).stem / "480p15"
            if output_dir.exists():
                mp4_files = list(output_dir.glob("*.mp4"))
                if mp4_files:
                    print(f"  Output file: {mp4_files[0]}")
                    print(f"  Size: {mp4_files[0].stat().st_size} bytes")
            
            print(f"\n✅ TEST PASSED")
            return True
        else:
            print(f"\n❌ Manim render FAILED")
            print(f"\n📄 STDOUT:")
            print(result.stdout[:1000])
            print(f"\n📄 STDERR:")
            print(result.stderr[:1000])
            
            print(f"\n❌ TEST FAILED")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n❌ TEST FAILED: Manim render timed out (>60s)")
        return False
    except FileNotFoundError:
        print(f"\n❌ TEST FAILED: Manim command not found")
        print(f"  Make sure Manim v0.19.0 is installed:")
        print(f"  pip install manim==0.19.0")
        return False
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        try:
            Path(temp_file).unlink()
        except:
            pass


if __name__ == "__main__":
    success = test_manim_render()
    sys.exit(0 if success else 1)
