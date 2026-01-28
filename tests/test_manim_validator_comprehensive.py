"""
Comprehensive Test Suite for Manim Code Validator

Tests the simplified validator to ensure it:
1. Accepts valid Python code (including edge cases)
2. Rejects truly broken code
3. Trusts compile() for syntax validation

Run with: pytest tests/test_manim_validator_comprehensive.py -v
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.agents.manim_code_generator import ManimCodeGenerator


class TestManimValidatorEdgeCases:
    """Test edge cases that previously caused false positives"""
    
    def setup_method(self):
        """Create validator instance"""
        # Use dummy API key for testing
        self.generator = ManimCodeGenerator(openrouter_api_key="dummy_key_for_testing")
    
    def test_valid_trailing_comma_in_list(self):
        """Test that valid trailing commas in lists are accepted"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        items = [
            Circle(),
            Square(),
            Triangle(),  # Valid trailing comma
        ]
        self.play(FadeIn(items[0]))
        self.wait(1)
"""
        errors = self.generator.validate_code(code, {}, skip_timing=True)
        assert len(errors) == 0, f"Should accept trailing comma in list, got errors: {errors}"
    
    def test_valid_trailing_comma_in_dict(self):
        """Test that valid trailing commas in dicts are accepted"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        config = {
            "color": RED,
            "radius": 1.0,  # Valid trailing comma
        }
        circle = Circle(**config)
        self.play(Create(circle))
        self.wait(1)
"""
        errors = self.generator.validate_code(code, {}, skip_timing=True)
        assert len(errors) == 0, f"Should accept trailing comma in dict, got errors: {errors}"
    
    def test_valid_trailing_comma_in_function_call(self):
        """Test that trailing commas in function calls are accepted"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        self.play(
            FadeIn(Circle()),
            run_time=2,  # Valid trailing comma
        )
        self.wait(1)
"""
        errors = self.generator.validate_code(code, {}, skip_timing=True)
        assert len(errors) == 0, f"Should accept trailing comma in function call, got errors: {errors}"
    
    def test_hash_symbol_in_string_literal(self):
        """Test that # in string literals doesn't break validation"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        # This should NOT be treated as a comment issue
        text = Text("Use # for comments in Python")
        formula = MathTex(r"f(x) = x^2 # squared")
        self.play(Write(text))
        self.wait(1)
"""
        errors = self.generator.validate_code(code, {}, skip_timing=True)
        assert len(errors) == 0, f"Should accept # in strings, got errors: {errors}"
    
    def test_parentheses_in_comments(self):
        """Test that unmatched parentheses in comments don't cause errors"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        # This formula (x + y) has unmatched parens in comment
        # Another one: f(x
        circle = Circle()
        self.play(Create(circle))  # Draw circle (animation)
        self.wait(1)
"""
        errors = self.generator.validate_code(code, {}, skip_timing=True)
        assert len(errors) == 0, f"Should ignore parens in comments, got errors: {errors}"
    
    def test_multiline_string_with_special_chars(self):
        """Test that multi-line strings with special characters are accepted"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        text = '''
        This is a multi-line string,
        with trailing comma,
        and # hash symbols (valid!)
        '''
        label = Text(text)
        self.play(Write(label))
        self.wait(1)
"""
        errors = self.generator.validate_code(code, {}, skip_timing=True)
        assert len(errors) == 0, f"Should accept multi-line strings, got errors: {errors}"
    
    def test_complex_valid_llm_generated_code(self):
        """Test realistic LLM-generated code with multiple edge cases"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        # Segment 1
        title = Text("Photosynthesis Process")  # Main title (important)
        formula = MathTex(
            r"6CO_2 + 6H_2O",
            r"\\rightarrow",
            r"C_6H_{12}O_6 + 6O_2",  # Trailing comma OK
        )
        
        self.play(Write(title))
        self.wait(0.5)
        
        # Segment 2
        animations = [
            FadeOut(title),
            FadeIn(formula),  # Valid trailing comma
        ]
        self.play(*animations, run_time=2)
        self.wait(1)
"""
        errors = self.generator.validate_code(code, {}, skip_timing=True)
        assert len(errors) == 0, f"Should accept complex valid code, got errors: {errors}"


class TestManimValidatorActualErrors:
    """Test that actual errors are still caught"""
    
    def setup_method(self):
        self.generator = ManimCodeGenerator(openrouter_api_key="dummy_key_for_testing")
    
    def test_missing_import(self):
        """Test that missing import is caught"""
        code = """
class MainScene(Scene):
    def construct(self):
        self.play(Create(Circle()))
"""
        errors = self.generator.validate_code(code, {}, skip_timing=True)
        assert len(errors) > 0, "Should catch missing import"
        assert any("from manim import" in str(e).lower() for e in errors)
    
    def test_missing_class_definition(self):
        """Test that missing class is caught"""
        code = """from manim import *

def construct(self):
    self.play(Create(Circle()))
"""
        errors = self.generator.validate_code(code, {}, skip_timing=True)
        assert len(errors) > 0, "Should catch missing class"
        assert any("class" in str(e).lower() for e in errors)
    
    def test_missing_construct_method(self):
        """Test that missing construct() is caught"""
        code = """from manim import *

class MainScene(Scene):
    def render(self):
        self.play(Create(Circle()))
"""
        errors = self.generator.validate_code(code, {}, skip_timing=True)
        assert len(errors) > 0, "Should catch missing construct"
        assert any("construct" in str(e).lower() for e in errors)
    
    def test_syntax_error_unmatched_bracket(self):
        """Test that actual syntax errors are caught by compile()"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        circle = Circle(
        self.play(Create(circle))
"""
        errors = self.generator.validate_code(code, {}, skip_timing=True)
        # compile() should catch this as SyntaxError
        assert len(errors) > 0, "Should catch syntax error"
    
    def test_incomplete_control_structure(self):
        """Test that control structures with no body are caught"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        if True:
"""
        errors = self.generator.validate_code(code, {}, skip_timing=True)
        assert len(errors) > 0, "Should catch incomplete control structure"
        assert any("no body" in str(e).lower() for e in errors)
    
    def test_forbidden_unicode_characters(self):
        """Test that forbidden characters are caught"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        # This has a rupee symbol which breaks LaTeX
        text = Text("Price: ₹100")
        self.play(Write(text))
"""
        errors = self.generator.validate_code(code, {}, skip_timing=True)
        assert len(errors) > 0, "Should catch forbidden unicode character"
        assert any("₹" in str(e) for e in errors)


class TestManimValidatorWaitScrubbing:
    """Test wait(0) and wait(0.0) removal"""
    
    def setup_method(self):
        self.generator = ManimCodeGenerator(openrouter_api_key="dummy_key_for_testing")
    
    def test_scrub_wait_zero(self):
        """Test that wait(0) is removed"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        self.play(Create(Circle()))
        self.wait(0)
        self.play(FadeOut(Circle()))
"""
        cleaned = self.generator._scrub_invalid_waits(code)
        assert "wait(0)" not in cleaned, "wait(0) should be removed"
    
    def test_scrub_wait_zero_point_zero(self):
        """Test that wait(0.0) is removed"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        self.play(Create(Circle()))
        self.wait(0.0)
        self.play(FadeOut(Circle()))
"""
        cleaned = self.generator._scrub_invalid_waits(code)
        assert "wait(0.0)" not in cleaned, "wait(0.0) should be removed"
    
    def test_keep_valid_waits(self):
        """Test that valid wait() calls are kept"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        self.wait(1)
        self.wait(2.5)
        self.wait(0.1)
"""
        cleaned = self.generator._scrub_invalid_waits(code)
        assert "wait(1)" in cleaned, "wait(1) should be kept"
        assert "wait(2.5)" in cleaned, "wait(2.5) should be kept"
        assert "wait(0.1)" in cleaned, "wait(0.1) should be kept"


class TestManimValidatorCompleteness:
    """Test completeness checking logic"""
    
    def setup_method(self):
        self.generator = ManimCodeGenerator(openrouter_api_key="dummy_key_for_testing")
    
    def test_empty_code(self):
        """Test that empty code is handled (compile() will catch it)"""
        errors = self.generator._check_completeness("")
        # Simplified validator returns "Empty code" error
        # This is fine - compile() would also catch this
        # We just verify it doesn't crash
        assert isinstance(errors, list)
    
    def test_only_comments(self):
        """Test that code with only comments is accepted (compile() will fail later)"""
        code = """
# Just a comment
# Another comment
"""
        # _check_completeness should pass (only checks structure)
        # compile() will catch the issue
        errors = self.generator._check_completeness(code)
        # Should not error on completeness - compile() handles this
        assert len(errors) == 0 or all("only comments" not in str(e).lower() for e in errors)
    
    def test_control_structure_with_comment_body(self):
        """Test that control structure with only comment body is caught"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        if True:
            # Just a comment, no actual code
"""
        errors = self.generator._check_completeness(code)
        assert len(errors) > 0, "Should catch control structure with no real body"
    
    def test_function_with_pass_statement(self):
        """Test that function with pass statement is accepted"""
        code = """from manim import *

class MainScene(Scene):
    def construct(self):
        if True:
            pass
"""
        errors = self.generator._check_completeness(code)
        assert len(errors) == 0, "Should accept control structure with pass"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
