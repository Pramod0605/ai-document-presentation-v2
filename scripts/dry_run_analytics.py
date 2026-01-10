
import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from core.pipeline_unified import process_markdown_unified

def run_dry_test():
    """Run a dry-run of the pipeline and verify analytics output."""
    logging.basicConfig(level=logging.INFO)
    
    job_id = "analytics_dry_run_01"
    output_dir = Path(f"jobs/{job_id}")
    
    # Clean previous run
    if output_dir.exists():
        import shutil
        try:
            shutil.rmtree(output_dir)
        except:
            pass
            
    markdown_content = """# Test Presentation
## Section 1: Intro
This is an introduction.
## Section 2: Content
Here is some content with a concept.
"""

    print(f"Starting Dry Run for Job {job_id}...")
    
    # MOCK the generator to avoid API keys
    import unittest.mock as mock
    # We need to patch where it is used. It is used in pipeline_unified.py via import
    
    try:
        # Patch the class in the module where it's defined
        with mock.patch('core.partition_director_generator.PartitionDirectorGenerator.generate_presentation_partitioned') as mock_gen:
            mock_gen.return_value = {
                "title": "Test Presentation",
                "sections": [
                    {
                        "section_id": "sec_1",
                        "title": "Intro",
                        "section_type": "intro",
                        "narration": {"segments": [{"text": "Hello"}]},
                        "renderer": "manim",
                        "explanation_plan": "Show text",
                        "visual_description": "Text on screen"
                    },
                    {
                        "section_id": "sec_2",
                        "title": "Main",
                        "section_type": "content",
                        "narration": {"segments": [{"text": "Content"}]},
                        "renderer": "video",
                        "explanation_plan": "Show video",
                        "visual_description": "Video of concept"
                    }
                ],
                "metadata": {"chunks": 1, "llm_calls": 0},
                "decision_log": {}
            }
            
            presentation, tracker = process_markdown_unified(
                markdown_content=markdown_content,
                subject="Testing",
                grade="University",
                job_id=job_id,
                generate_tts=False, # Dry run skips TTS
                output_dir=output_dir,
                dry_run=True, # Critical: uses dry-run renderers
                skip_wan=True,
                pipeline_version="v15_v2_director"
            )
        
        print("Pipeline finished.")
        
        # Verify Analytics File
        analytics_path = output_dir / "analytics.json"
        if not analytics_path.exists():
            print("FAILED: analytics.json not found!")
            return False
            
        with open(analytics_path, "r") as f:
            data = json.load(f)
            
        print("\n--- Analytics Verification ---")
        
        # Check Timings
        timings = data.get("timings", {})
        print(f"Timings found: {list(timings.keys())}")
        if "llm_generation" not in timings and "visual_rendering" not in timings:
             print("WARNING: Expected phases (llm_generation, visual_rendering) not found in timings.")
        
        # Check Renderer Details
        renderer = data.get("renderer", {})
        details = renderer.get("details", [])
        print(f"Renderer Details: {len(details)} items")
        if details:
            print(f"Sample Detail: {details[0]}")
            if "retry_action" in details[0]: 
                print("Retry action found (checked)")
        
        pass_check = True
        
        # Check Phase Breakdown
        phases = data.get("phases", [])
        print(f"Phases found: {[p.get('phase_name') for p in phases]}")
        
        return True
        
    except Exception as e:
        print(f"Dry Run Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_dry_test()
    sys.exit(0 if success else 1)
