
import unittest
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from render.wan.kie_batch_generator import KieBatchGenerator

class TestWanRetryLogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.generator = KieBatchGenerator(api_key="fake_key")
        # Mock the API creation to avoid real calls
        self.generator._create_task = MagicMock(return_value="task_123")
        self.generator._poll_all_tasks = MagicMock(return_value={})

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_skip_existing_files(self):
        # 1. Create a dummy existing file
        existing_beat_id = "beat_exists"
        existing_file = os.path.join(self.test_dir, f"{existing_beat_id}.mp4")
        with open(existing_file, "w") as f:
            f.write("dummy content") # Non-zero size

        # 2. Define batch with mixed existing and new beats
        beats = [
            {"beat_id": existing_beat_id, "prompt": "p1", "duration_hint": 5},
            {"beat_id": "beat_new", "prompt": "p2", "duration_hint": 5}
        ]

        # 3. Run generation
        print("\n--- Test Output Start ---")
        results = self.generator.generate_batch(beats, self.test_dir)
        print("--- Test Output End ---\n")

        # 4. Verify results
        # The existing file should be in results with its local path
        self.assertIn(existing_beat_id, results)
        self.assertEqual(results[existing_beat_id], existing_file)
        
        # Verify _create_task was called ONLY ONCE (for the new beat)
        self.generator._create_task.assert_called_once()
        args, _ = self.generator._create_task.call_args
        self.assertIn("p2", args) # Should be the new prompt

if __name__ == "__main__":
    unittest.main()
