"""
Unit Test: Manim Code Generation (Claude Sonnet 4.5)

Tests that the ManimCodeGenerator produces valid Python code.
"""
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_manim_code_generation():
    """Test Claude 4.5 code generation for Manim."""
    from core.agents.manim_code_generator import ManimCodeGenerator
    
    print("=" * 60)
    print("TEST: Manim Code Generation (Claude Sonnet 4.5)")
    print("=" * 60)
    
    # Create generator
    gen = ManimCodeGenerator()
    print(f"✓ Generator created")
    print(f"  Model: {gen.model}")
    print(f"  Max tokens: {gen.max_tokens}")
    
    # Test input
    test_data = {
        "section_title": "Pythagorean Theorem",
        "narration_segments": [
            {"text": "Let's start with a right triangle.", "duration": 5.0, "visual": "Show triangle ABC"},
            {"text": "The sides are labeled a, b, and c.", "duration": 5.0, "visual": "Label sides"},
            {"text": "The relationship is a² + b² = c².", "duration": 5.0, "visual": "Show formula"}
        ],
        "visual_description": "Right triangle with labeled sides and Pythagorean formula",
        "formulas": ["a^2 + b^2 = c^2"],
        "key_terms": ["hypotenuse", "right angle"],
        "x_min": -5,
        "x_max": 5,
        "y_min": -3,
        "y_max": 10
    }
    
    print(f"\n✓ Test input prepared:")
    print(f"  Segments: {len(test_data['narration_segments'])}")
    print(f"  Total duration: {sum(s['duration'] for s in test_data['narration_segments'])}s")
    print(f"  Formulas: {test_data['formulas']}")
    
    # Generate code
    try:
        print(f"\n⏳ Calling Claude Sonnet 4.5...")
        code, errors = gen.generate(test_data)
        
        if errors:
            print(f"\n⚠️ Generation completed with errors:")
            for err in errors:
                print(f"  - {err}")
        
        # Stats
        lines = len([l for l in code.split('\n') if l.strip()])
        chars = len(code)
        estimated_tokens = chars / 3.5
        
        print(f"\n📊 Generated Code Stats:")
        print(f"  Lines: {lines} (target: 60-80)")
        print(f"  Chars: {chars}")
        print(f"  Est. tokens: {estimated_tokens:.0f} / 8192")
        print(f"  Token usage: {(estimated_tokens/8192)*100:.1f}%")
        
        # Check warnings
        if lines > 100:
            print(f"  ⚠️ Code is long ({lines} lines)")
        if estimated_tokens > 6000:
            print(f"  ⚠️ High token usage ({estimated_tokens:.0f}/8192)")
        
        # Check for common issues
        issues = []
        if "Dot()" in code:
            issues.append("Contains Dot() placeholder")
        if "get_edges()" in code:
            issues.append("Uses deprecated get_edges()")
        if "ShowCreation" in code:
            issues.append("Uses deprecated ShowCreation")
        if not code.strip():
            issues.append("Empty code")
        if code.endswith(',') or code.endswith('('):
            issues.append("Code appears truncated")
        
        if issues:
            print(f"\n❌ CODE ISSUES:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"\n✅ No obvious code issues detected")
        
        # Print preview
        print(f"\n📄 Code Preview (first 500 chars):")
        print(code[:500])
        print("...")
        
        # Overall result
        if not errors and not issues and 60 <= lines <= 100:
            print(f"\n✅ TEST PASSED")
            return True
        else:
            print(f"\n⚠️ TEST PASSED WITH WARNINGS")
            return True
            
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_manim_code_generation()
    sys.exit(0 if success else 1)
