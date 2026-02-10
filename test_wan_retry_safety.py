import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from render.wan.kie_batch_generator import KieBatchGenerator
from render.wan.wan_client import WanSafetyError, WanFatalError

class TestWanRetrySafety(unittest.TestCase):
    @patch('requests.post')
    @patch('core.llm_client.openrouter.chat.completions.create')
    def test_safety_retry_logic(self, mock_llm, mock_post):
        """Test that a 422 Safety Error triggers LLM rewrite and retry."""
        
        # Setup Generator
        generator = KieBatchGenerator(api_key="sk-test-key")
        generator._poll_all_tasks = MagicMock(return_value={}) # MOCK POLLING to simplify

        unsafe_prompt = "Extreme close-up on a young Indian woman's hands carefully filling out an official government form..."
        safe_prompt = "Medium shot of an adult individual writing at a desk..."
        
        beats = [{
            "beat_id": "test_beat_1",
            "prompt": unsafe_prompt,
            "duration_hint": 5
        }]
        
        # 1. Mock LLM response for REWRITE
        # Note: KieBatchGenerator might call _rewrite_prompt multiple times or just once.
        # Here we mock it returning the SAFE prompt.
        mock_llm_response = MagicMock()
        mock_llm_response.choices[0].message.content = safe_prompt
        # Also need to handle potential multiple calls if logic is tricky, but return_value is fine for singular path
        mock_llm.return_value = mock_llm_response
        
        # 2. Mock API responses for requests.post (The submission)
        # Call 1: 422 Safety Error
        resp1 = MagicMock()
        resp1.status_code = 422
        resp1.text = "Safety check failed: NSFW content detected"
        
        # Call 2: 200 OK (Task Created)
        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = {"code": 200, "data": {"taskId": "task_123"}}
        
        # Patch KieBatchGenerator to use our mock responses via requests
        mock_post.side_effect = [resp1, resp2]
        
        # Execute
        print("\n--- Starting Safety Retry Test ---")
        generator.generate_batch(beats, "test_output")
        
        # Verify
        print("\n--- Verifying Results ---")
        
        # Check LLM called with SAFETY prompt
        mock_llm.assert_called()
        # Find the call args that contain safety rules
        safety_call_found = False
        for call in mock_llm.call_args_list:
            if "HARD SAFETY RULES" in str(call):
                safety_call_found = True
                break
        self.assertTrue(safety_call_found, "LLM was not called with Hard Safety Rules")
        print("✅ LLM called with Hard Safety Rules")
        
        # Check API called twice for submission
        # Note: Since I patched requests.post globally, verify call count
        # BUT: KieBatchGenerator._create_task calls requests.post.
        # AND: If polling was NOT mocked correctly it might call too. But I mocked `_poll_all_tasks`.
        
        # Filter calls related to current test flow if strictly needed, but let's assume cleanup between tests
        self.assertEqual(mock_post.call_count, 2, f"Expected 2 API calls, got {mock_post.call_count}")
        
        # Check Call 1: Unsafe Prompt
        call1_args = mock_post.call_args_list[0]
        json_payload1 = call1_args[1]['json']
        self.assertIn(unsafe_prompt[:20], json_payload1['input']['prompt'])
        print("✅ Attempt 1: Submitted Original Prompt (Failed 422)")
        
        # Check Call 2: Safe Prompt
        call2_args = mock_post.call_args_list[1]
        json_payload2 = call2_args[1]['json']
        self.assertIn(safe_prompt[:20], json_payload2['input']['prompt'])
        print("✅ Attempt 2: Submitted Rewritten Safe Prompt (Success 200)")

    @patch('requests.post')
    @patch('core.llm_client.openrouter.chat.completions.create')
    def test_feedback_retry_logic(self, mock_llm, mock_post):
        """Test that user_feedback triggers prompt rewrite BEFORE submission."""
        
        generator = KieBatchGenerator(api_key="sk-test-key")
        generator._poll_all_tasks = MagicMock(return_value={}) 

        original_prompt = "A cat sitting on a mat."
        feedback = "Make the cat orange."
        rewritten_prompt = "An orange cat sitting on a mat."
        
        beats = [{
            "beat_id": "test_beat_2",
            "prompt": original_prompt,
            "duration_hint": 5
        }]
        
        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.choices[0].message.content = rewritten_prompt
        mock_llm.return_value = mock_llm_response
        
        # Mock API response (Success first try)
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"code": 200, "data": {"taskId": "task_456"}}
        mock_post.return_value = resp
        
        # Execute with feedback
        print("\n--- Starting Feedback Rewrite Test ---")
        generator.generate_batch(beats, "test_output", user_feedback=feedback)
        
        # Verify
        print("\n--- Verifying Feedback Results ---")
        
        # Check LLM called with FEEDBACK prompt
        mock_llm.assert_called_once()
        call_args = mock_llm.call_args
        self.assertIn(feedback, str(call_args))
        print("✅ LLM called with User Feedback")
        
        # Check API called with NEW prompt
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        json_payload = call_args[1]['json']
        self.assertEqual(json_payload['input']['prompt'], rewritten_prompt)
        print("✅ Attempt 1: Submitted Feedback-Enhanced Prompt")

if __name__ == '__main__':
    unittest.main()
