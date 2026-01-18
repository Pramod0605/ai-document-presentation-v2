
import os
import sys
import json
import unittest
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from core.validators.job_certifier import JobCertifier
from core.partition_director_generator import PartitionDirectorGenerator

class TestSurgicalFixes(unittest.TestCase):
    
    def test_recap_malformed_fix(self):
        """Test that JobCertifier handles dictionary-based video prompts in Recap."""
        mock_presentation = {
            "sections": [
                {
                    "section_type": "recap",
                    "video_prompts": [
                        {"beat_id": "b1", "prompt": "This is a very long and detailed cinematic prompt that should definitely pass the word count check since it has more than eighty words in total for the purpose of testing the fix for the malformed structure error which was previously caused by calling split on a dictionary instead of a string value."},
                        "This is a string prompt that should also work fine because the code now handles both types of inputs gracefully using the isinstance check we just implemented."
                    ]
                }
            ]
        }
        
        # We need to mock the file read since certify_job reads from disk
        temp_dir = Path("tests/temp_job")
        temp_dir.mkdir(parents=True, exist_ok=True)
        pres_path = temp_dir / "presentation.json"
        
        try:
            with open(pres_path, "w", encoding="utf-8") as f:
                json.dump(mock_presentation, f)
            
            result = JobCertifier.certify_job(str(temp_dir))
            
            # Check the report content
            report_path = temp_dir / "certification_report.txt"
            with open(report_path, "r", encoding="utf-8") as f:
                report = f.read()
            
            self.assertNotIn("Recap Error: Malformed structure", report)
            print("[PASS] Recap Malformed Fix Verified")
            
        finally:
            if pres_path.exists(): os.remove(pres_path)
            if (temp_dir / "certification_report.txt").exists(): os.remove(temp_dir / "certification_report.txt")
            if temp_dir.exists(): temp_dir.rmdir()

    def test_wan_id_uniqueness(self):
        """Test that _apply_sync_splitter uses the correct section_id for beat IDs."""
        generator = PartitionDirectorGenerator()
        
        # Mock section with assigned global ID
        mock_section = {
            "section_id": 12,
            "renderer": "video",
            "narration": {
                "segments": [
                    {"segment_id": "seg_1", "duration_seconds": 10, "display_directives": {"visual_layer": "show"}}
                ]
            }
        }
        
        generator._apply_sync_splitter(mock_section)
        
        prompts = mock_section.get("video_prompts", [])
        self.assertTrue(len(prompts) > 0)
        self.assertTrue(prompts[0]["beat_id"].startswith("topic_12_"))
        print(f"[PASS] WAN ID Uniqueness Verified: {prompts[0]['beat_id']}")

if __name__ == "__main__":
    unittest.main()
