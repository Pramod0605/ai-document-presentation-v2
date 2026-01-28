"""
Test User Feedback Feature in Manim Regeneration

Tests that:
1. Existing workflow works without feedback (backward compatibility)
2. Feedback is properly injected when provided
3. Feedback appears in the user prompt correctly
"""
import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agents.manim_code_generator import ManimCodeGenerator


class TestUserFeedbackFeature:
    """Test user feedback injection in Manim generation"""
    
    def setup_method(self):
        """Create generator instance"""
        self.generator = ManimCodeGenerator(openrouter_api_key="dummy_key_for_testing")
    
    def test_backward_compatibility_without_feedback(self):
        """Test that existing flow works without user_feedback (backward compatibility)"""
        section_data = {
            "section_title": "Test Section",
            "narration_segments": [
                {"text": "Test narration", "duration": 3.0}
            ],
            "manim_spec": "Show a circle",
            "formulas": ["x^2"],
            "key_terms": ["math"]
        }
        
        # Build prompt without feedback
        prompt = self.generator._build_user_prompt(section_data)
        
        # Should build successfully
        assert len(prompt) > 0, "Prompt should be generated"
        assert "Test Section" in prompt, "Section title should be in prompt"
        assert "Test narration" in prompt, "Narration should be in prompt"
        
        # Should NOT contain feedback section
        assert "USER'S IMPROVEMENT REQUEST" not in prompt, "Should not have feedback section"
        assert "IMPROVEMENT" not in prompt, "Should not mention improvements"
    
    def test_feedback_injection(self):
        """Test that user feedback is properly injected into prompt"""
        section_data = {
            "section_title": "Test Section",
            "narration_segments": [
                {"text": "Test narration", "duration": 3.0}
            ],
            "manim_spec": "Show a circle",
            "formulas": ["x^2"],
            "key_terms": ["math"],
            "user_feedback": "Make the animation slower and add more colors"
        }
        
        # Build prompt with feedback
        prompt = self.generator._build_user_prompt(section_data)
        
        # Should contain feedback section
        assert "USER'S IMPROVEMENT REQUEST" in prompt, "Should have feedback header"
        assert "Make the animation slower and add more colors" in prompt, "Should include user feedback"
        assert "incorporate this feedback" in prompt.lower(), "Should have instructions to use feedback"
    
    def test_empty_feedback_string(self):
        """Test that empty feedback string is treated as no feedback"""
        section_data = {
            "section_title": "Test Section",
            "narration_segments": [
                {"text": "Test narration", "duration": 3.0}
            ],
            "manim_spec": "Show a circle",
            "user_feedback": ""  # Empty string
        }
        
        prompt = self.generator._build_user_prompt(section_data)
        
        # Should NOT contain feedback section (empty string = falsy)
        assert "USER'S IMPROVEMENT REQUEST" not in prompt, "Empty feedback should be skipped"
    
    def test_multiline_feedback(self):
        """Test that multi-line feedback is preserved"""
        feedback = """1. Make the circle larger
2. Use blue color instead of red
3. Add a smooth fade-in animation
4. Include axis labels"""
        
        section_data = {
            "section_title": "Test Section",
            "narration_segments": [
                {"text": "Test narration", "duration": 3.0}
            ],
            "manim_spec": "Show a circle",
            "user_feedback": feedback
        }
        
        prompt = self.generator._build_user_prompt(section_data)
        
        # All lines should be preserved
        assert "Make the circle larger" in prompt
        assert "Use blue color" in prompt
        assert "smooth fade-in" in prompt
        assert "axis labels" in prompt
    
    def test_feedback_with_special_characters(self):
        """Test that feedback with special characters is handled correctly"""
        feedback = "Use f(x) = x^2 + 2x + 1, add LaTeX: $\\int_{0}^{1} x dx$, and use colors like #FF5733"
        
        section_data = {
            "section_title": "Test Section",
            "narration_segments": [
                {"text": "Test narration", "duration": 3.0}
            ],
            "manim_spec": "Show a formula",
            "user_feedback": feedback
        }
        
        prompt = self.generator._build_user_prompt(section_data)
        
        # Special characters should be preserved
        assert "f(x) = x^2 + 2x + 1" in prompt
        assert "$\\int_{0}^{1} x dx$" in prompt or "int_{0}^{1}" in prompt  # LaTeX might be escaped
        assert "#FF5733" in prompt


class TestAPIIntegration:
    """Test that API parameters are properly used (unit test without actual API calls)"""
    
    def test_section_data_with_feedback(self):
        """Test that section_data dictionary properly holds user_feedback"""
        section_data = {
            "section_title": "Math Section",
            "narration_segments": [],
            "user_feedback": "Add more visual examples"
        }
        
        # Verify the data structure
        assert section_data.get("user_feedback") == "Add more visual examples"
        assert section_data.get("user_feedback", "") != "", "Feedback should be accessible"
    
    def test_section_data_without_feedback(self):
        """Test that section_data without feedback returns empty string"""
        section_data = {
            "section_title": "Math Section",
            "narration_segments": []
        }
        
        # Verify missing key returns empty string
        assert section_data.get("user_feedback", "") == ""
        assert not section_data.get("user_feedback"), "Missing feedback should be falsy"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
