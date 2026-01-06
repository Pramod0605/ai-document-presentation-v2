
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import json
import os
import sys

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tts_duration import update_durations_simplified

class TestTTSSimplified(unittest.TestCase):
    def setUp(self):
        self.test_presentation = {
            "sections": [
                {
                    "section_id": "section_1",
                    "narration": {
                        "segments": [
                            {"segment_id": "seg_1", "text": "Hello world"},
                            {"segment_id": "seg_2", "text": "This is a test"}
                        ]
                    }
                }
            ]
        }
        self.output_dir = Path("test_output")
        self.output_dir.mkdir(exist_ok=True)

    def tearDown(self):
        import shutil
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)

    @patch("core.tts_duration._generate_edge_tts")
    def test_update_durations_simplified_parallel(self, mock_gen):
        # Mocking audio generation success
        mock_gen.return_value = 1.5
        
        # We need to simulate the file being created since the code checks audio_path.exists()
        def side_effect(text, path):
            Path(path).touch()
            return 1.5
        mock_gen.side_effect = side_effect

        # Run the function
        updated_pres = update_durations_simplified(
            self.test_presentation,
            output_dir=self.output_dir,
            production_provider="edge_tts"
        )

        # Check if segments have audio_file link
        segments = updated_pres["sections"][0]["narration"]["segments"]
        self.assertIn("audio_file", segments[0])
        self.assertIn("audio_file", segments[1])
        print("[TEST] update_durations_simplified_parallel PASSED")

if __name__ == "__main__":
    unittest.main()
