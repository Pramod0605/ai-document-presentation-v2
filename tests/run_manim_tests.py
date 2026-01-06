"""
Test Runner: Execute all Manim unit tests in sequence

Runs:
1. test_manim_spec.py - Gemini 2.5 Pro spec generation
2. test_manim_code.py - Claude 4.5 code generation  
3. test_manim_render.py - Manim v0.19.0 rendering

Outputs a summary report identifying exactly which component fails.
"""
import subprocess
import sys
from pathlib import Path

def run_test(test_file: str, test_name: str) -> tuple[bool, str]:
    """Run a single test file and return success status + output."""
    print(f"\n{'='*60}")
    print(f"Running: {test_name}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        output = result.stdout + result.stderr
        print(output)
        
        success = result.returncode == 0
        return success, output
        
    except subprocess.TimeoutExpired:
        msg = f"❌ {test_name} TIMED OUT (>120s)"
        print(msg)
        return False, msg
    except Exception as e:
        msg = f"❌ {test_name} EXCEPTION: {e}"
        print(msg)
        return False, msg


def main():
    """Run all tests and report results."""
    print("=" * 60)
    print("MANIM PIPELINE ISOLATION TESTS")
    print("=" * 60)
    print(f"\nPurpose: Identify exact failure point in Manim pipeline")
    print(f"Tests: Spec Gen → Code Gen → Rendering")
    
    tests_dir = Path(__file__).parent
    
    tests = [
        (tests_dir / "test_manim_spec.py", "1. Manim Spec Generation (Gemini 2.5 Pro)"),
        (tests_dir / "test_manim_code.py", "2. Manim Code Generation (Claude 4.5)"),
        (tests_dir / "test_manim_render.py", "3. Manim Rendering (v0.19.0)")
    ]
    
    results = {}
    
    for test_file, test_name in tests:
        if not test_file.exists():
            print(f"\n⚠️ SKIPPING {test_name}: File not found")
            results[test_name] = ("skipped", f"File not found: {test_file}")
            continue
        
        success, output = run_test(str(test_file), test_name)
        results[test_name] = ("passed" if success else "failed", output)
        
        # Stop on first failure for faster debugging
        if not success:
            print(f"\n🛑 Stopping at first failure: {test_name}")
            break
    
    # Summary Report
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, (status, _) in results.items():
        icon = "✅" if status == "passed" else "❌" if status == "failed" else "⏭️"
        print(f"{icon} {test_name}: {status.upper()}")
    
    # Diagnosis
    print("\n" + "=" * 60)
    print("DIAGNOSIS")
    print("=" * 60)
    
    failed_tests = [name for name, (status, _) in results.items() if status == "failed"]
    
    if not failed_tests:
        print("✅ All tests passed! Pipeline is healthy.")
        print("\nIf videos still aren't generating, check:")
        print("  - API keys in .env")
        print("  - Docker container status")
        print("  - Job presentation.json structure")
        return 0
    else:
        first_failure = failed_tests[0]
        print(f"🔍 First failure: {first_failure}")
        
        if "Spec Generation" in first_failure:
            print("\n💡 RECOMMENDATION:")
            print("  Issue is in SPEC GENERATION (Gemini 2.5 Pro)")
            print("  Possible causes:")
            print("    - OPENROUTER_API_KEY missing or invalid")
            print("    - Gemini 2.5 Pro model unavailable")
            print("    - Prompt format issue")
            print("    - Network/API connectivity")
        
        elif "Code Generation" in first_failure:
            print("\n💡 RECOMMENDATION:")
            print("  Issue is in CODE GENERATION (Claude 4.5)")
            print("  Possible causes:")
            print("    - OPENROUTER_API_KEY missing or invalid")
            print("    - Claude 4.5 model unavailable/access denied")
            print("    - Prompt causing errors")
            print("    - Code truncation (check logs for 'finish_reason: length')")
        
        elif "Rendering" in first_failure:
            print("\n💡 RECOMMENDATION:")
            print("  Issue is in RENDERING (Manim v0.19.0)")
            print("  Possible causes:")
            print("    - Manim not installed (pip install manim==0.19.0)")
            print("    - Missing system dependencies (ffmpeg, latex, dvisvgm)")
            print("    - Python version mismatch (need 3.10.x)")
            print("    - Generated code has syntax errors")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
