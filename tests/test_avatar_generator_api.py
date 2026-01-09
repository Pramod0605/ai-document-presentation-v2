"""
Tests for core.agents.avatar_generator.AvatarGenerator

Run with:
    python tests/test_avatar_generator_api.py          # Run with mocks (default)
    python tests/test_avatar_generator_api.py --live   # Run against live API (requires AVATAR_API_URL in .env)
"""
import os
import sys
import unittest
import argparse
import requests
import json
from unittest.mock import MagicMock, patch, call
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agents.avatar_generator import AvatarGenerator

class TestAvatarGenerator(unittest.TestCase):
    
    def setUp(self):
        # Setup specific to each test method if needed
        self.mock_api_url = "http://mock-api:5003/api"
        # We patch latex_to_speech to avoid needing its dependencies or logic for simple API tests
        self.lts_patcher = patch('core.agents.avatar_generator.latex_to_speech', side_effect=lambda x: x)
        self.mock_lts = self.lts_patcher.start()

    def tearDown(self):
        self.lts_patcher.stop()

    def test_init_raises_error_without_env_var(self):
        """Test that initialization fails if AVATAR_API_URL is missing and no url provided."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                AvatarGenerator()

    def test_init_with_env_var(self):
        """Test initialization with environment variable."""
        with patch.dict(os.environ, {"AVATAR_API_URL": self.mock_api_url}):
            ag = AvatarGenerator()
            self.assertEqual(ag.api_url, self.mock_api_url)

    @patch('requests.post')
    def test_generate_avatar_video_success_mock(self, mock_post):
        """Test successful generation request (Mocked)."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"task_id": "task_123", "status": "queued"}
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"AVATAR_API_URL": self.mock_api_url}):
            ag = AvatarGenerator()
            result = ag.generate_avatar_video("Hello world", "job_001", 1)

            self.assertEqual(result["task_id"], "task_123")
            self.assertEqual(result["status"], "queued")
            # Verify request
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            self.assertEqual(args[0], f"{self.mock_api_url}/generate")
            self.assertEqual(kwargs['data']['text'], "Hello world")

    @patch('requests.post')
    def test_generate_avatar_video_retry_logic(self, mock_post):
        """Test retry logic on 429 Rate Limit (Mocked)."""
        # First 2 calls return 429, 3rd returns 200
        r429 = MagicMock()
        r429.status_code = 429
        
        r200 = MagicMock()
        r200.status_code = 200
        r200.json.return_value = {"task_id": "task_retry_success"}

        mock_post.side_effect = [r429, r429, r200]

        with patch.dict(os.environ, {"AVATAR_API_URL": self.mock_api_url}):
            # Reduce sleep time for test speed
            with patch('time.sleep') as mock_sleep: 
                ag = AvatarGenerator()
                result = ag.generate_avatar_video("Retry me", "job_001", 1)

                self.assertEqual(result["task_id"], "task_retry_success")
                self.assertEqual(mock_post.call_count, 3)
                self.assertEqual(mock_sleep.call_count, 2)

    @patch('requests.get')
    def test_check_status_mock(self, mock_get):
        """Test status check (Mocked)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Simulated API response structure
        mock_response.json.return_value = {
            "task_id": "task_123",
            "task_status": {
                "status": "completed",
                "output": "http://some-url/video.mp4"
            }
        }
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {"AVATAR_API_URL": self.mock_api_url}):
            ag = AvatarGenerator()
            status = ag.check_status("task_123")
            
            self.assertEqual(status["status"], "completed")
            self.assertEqual(status["output_url"], "http://some-url/video.mp4")
            mock_get.assert_called_with(f"{self.mock_api_url}/status/task_123", timeout=10)

    @patch('core.agents.avatar_generator.AvatarGenerator.check_status')
    @patch('core.agents.avatar_generator.AvatarGenerator.download_video')
    @patch('core.agents.avatar_generator.AvatarGenerator.generate_avatar_video')
    def test_submit_parallel_job_batch_logic(self, mock_generate, mock_download, mock_status):
        """
        Verify that submit_parallel_job:
        1. Submitted 2 tasks (batch size 2).
        2. Waited for them to complete.
        3. Downloaded them.
        """
        # Setup Mock Data
        mock_presentation = {
            "sections": [
                {"section_id": 1, "narration": "Narration 1"},
                {"section_id": 2, "narration": "Narration 2"},
                # Just 2 for this test to match one batch
            ]
        }
        
        # Mock Generation: Success for both
        mock_generate.side_effect = [
            {"task_id": "task_1", "status": "queued"},
            {"task_id": "task_2", "status": "queued"}
        ]
        
        # Mock Status: 
        # Call 1 (task_1): processing
        # Call 2 (task_2): processing
        # Call 3 (task_1): completed
        # Call 4 (task_2): completed
        mock_status.side_effect = [
            {"status": "processing"},
            {"status": "processing"},
            {"status": "completed", "output_url": "http://vid1"},
            {"status": "completed", "output_url": "http://vid2"}
        ]
        
        # Mock Download: Success
        mock_download.return_value = True
        
        with patch.dict(os.environ, {"AVATAR_API_URL": self.mock_api_url}):
            with patch('time.sleep') as mock_sleep: # Skip waiting
                ag = AvatarGenerator()
                # Mock output dir creation
                with patch('pathlib.Path.mkdir'):
                     results = ag.submit_parallel_job(mock_presentation, "TEST_JOB", "dummy_out")
        
        # Assertions
        self.assertEqual(len(results["queued"]), 2)
        self.assertEqual(len(results["completed"]), 2)
        
        # Verify call order implicitly via effects, but mainly just success count
        self.assertEqual(mock_generate.call_count, 2)
        # 4 status checks (2 processing + 2 completed)
        self.assertEqual(mock_status.call_count, 4) 
        # 2 downloads
        self.assertEqual(mock_download.call_count, 2)


def run_live_tests():
    """Run tests against the actual configured API."""
    print("\n" + "="*60)
    print("RUNNING LIVE API TESTS")
    print("="*60)
    
    # Load .env manually since we might not have 'dotenv' in this specific isolated run or need to ensure it's loaded
    from dotenv import load_dotenv
    load_dotenv()

    api_url = os.environ.get("AVATAR_API_URL")
    if not api_url:
        print("ERROR: AVATAR_API_URL not found in environment. Cannot run live tests.")
        return

    print(f"Target API: {api_url}")
    
    try:
        ag = AvatarGenerator()
        
        # 1. Health/Info Check
        print("\n[1] Checking API Accessibility...")
        try:
            resp = requests.get(f"{api_url}/info", timeout=5)
            if resp.status_code == 200:
                print(f"    SUCCESS: API Info: {resp.json()}")
            else:
                print(f"    WARNING: /api/info returned {resp.status_code}")
        except Exception as e:
            print(f"    WARNING: Health check connection failed: {e}")

        # 2. Mock Narration Logic Test
        # Send 2 short requests to test batching
        print("\n[2] Testing Batch Processing (Live)...")
        # Create 5 sections to force 3 batches: [2, 2, 1]
        test_pres = {
            "sections": [
                 {"section_id": 101, "narration": "Batch 1, Item 1: Testing multi-batch synchronization."},
                 {"section_id": 102, "narration": "Batch 1, Item 2: This should finish before Batch 2 starts."},
                 {"section_id": 103, "narration": "Batch 2, Item 1: If you see this submit early, logic is broken."},
                 {"section_id": 104, "narration": "Batch 2, Item 2: Waiting for previous batch..."},
                 {"section_id": 105, "narration": "Batch 3, Item 1: Final batch single item."}
            ]
        }
        
        # Use a temp directory for downloads
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdirname:
            print(f"    Using temp dir: {tmpdirname}")
            
            results = ag.submit_parallel_job(test_pres, "LIVE_TEST_JOB", tmpdirname)
            
            print(f"\n[3] Results: {json.dumps(str(results), indent=2)}")
            
            # Verify files downloaded
            dl_files = list(Path(tmpdirname).rglob("*.mp4"))
            print(f"    Downloaded files ({len(dl_files)}): {[f.name for f in dl_files]}")
            
            if len(results.get('completed', [])) == 2 and len(dl_files) == 2:
                print("    SUCCESS: Batch processing submitted, waited, and downloaded both videos.")
            else:
                print("    WARNING: Not all files completed/downloaded.")

        print("\nDONE. Live test finished.")

    except Exception as e:
        print(f"\nCRITICAL FAILURE during live test: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run AvatarGenerator tests')
    parser.add_argument('--live', action='store_true', help='Run live API integration tests')
    
    # Parse args but keep argv clean for unittest if needed (though we separate logic)
    args, remaining_argv = parser.parse_known_args()
    
    if args.live:
        run_live_tests()
    else:
        # Run standard unit tests
        # We need to pass the remaining argv to unittest so it can handle other flags like -v
        sys.argv = [sys.argv[0]] + remaining_argv
        unittest.main()
