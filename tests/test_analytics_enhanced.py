
import unittest
import json
import os
import shutil
from pathlib import Path
from core.analytics import AnalyticsTracker, PipelineAnalytics

class TestEnhancedAnalytics(unittest.TestCase):
    def setUp(self):
        self.test_job_id = "test_job_123"
        self.tracker = AnalyticsTracker(self.test_job_id)
        self.output_file = "test_analytics.json"

    def tearDown(self):
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

    def test_progress_tracking(self):
        """Test that progress metrics can be updated and serialized."""
        # 1. Update progress
        self.tracker.update_progress(
            category="avatar_generation",
            completed=2,
            total=10,
            failed=1,
            message="Processing batch 1"
        )
        
        # 2. Check internal state
        progress = self.tracker.analytics.progress_details.get("avatar_generation")
        self.assertIsNotNone(progress)
        self.assertEqual(progress.completed, 2)
        self.assertEqual(progress.failed, 1)
        self.assertEqual(progress.total, 10)
        self.assertEqual(progress.pending, 7) # 10 - 2 - 1
        
        # 3. Serialize and check
        json_str = self.tracker.analytics.to_json()
        data = json.loads(json_str)
        self.assertIn("progress_details", data)
        self.assertEqual(data["progress_details"]["avatar_generation"]["completed"], 2)

    def test_renderer_retry_action(self):
        """Test that renderer details support retry actions."""
        self.tracker.add_render_detail(
            section_id="sec_1",
            section_type="content",
            renderer="manim",
            duration=12.5,
            status="failed",
            retry_action="/retry/manim/sec_1"
        )
        
        details = self.tracker.analytics.renderer.section_renders
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]["status"], "failed")
        self.assertEqual(details[0]["retry_action"], "/retry/manim/sec_1")

    def test_load_save_cycle(self):
        """Test that new fields survive a save/load cycle."""
        # Set some data
        self.tracker.update_progress("avatar", 5, 10)
        self.tracker.analytics.timings = {"llm": 15.0, "manim": 30.0}
        
        # Save
        self.tracker.save_to_file(self.output_file)
        
        # Load into new tracker
        new_tracker = AnalyticsTracker("restored_job")
        success = new_tracker.load_from_file(self.output_file)
        
        self.assertTrue(success)
        self.assertIn("avatar", new_tracker.analytics.progress_details)
        self.assertEqual(new_tracker.analytics.progress_details["avatar"].completed, 5)
        self.assertEqual(new_tracker.analytics.timings["llm"], 15.0)

if __name__ == '__main__':
    unittest.main()
