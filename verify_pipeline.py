import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.pipeline_unified import process_markdown_unified, PipelineUnifiedError
from core.analytics import AnalyticsTracker

def test_pipeline():
    print("Testing pipeline return types...")
    try:
        # Mock inputs
        md = "# Test"
        subject = "Test"
        grade = "9"
        job_id = "test_run"
        
        result = process_markdown_unified(
            markdown_content=md,
            subject=subject,
            grade=grade,
            job_id=job_id,
            dry_run=True, # Dry run skips heavy lifting
            pipeline_version="v15_v2_director",
            generation_scope="content"
        )
        
        if result is None:
            print("FAILURE: process_markdown_unified returned None!")
            sys.exit(1)
            
        presentation, tracker = result
        print(f"SUCCESS: Returned presentation ({type(presentation)}) and tracker ({type(tracker)})")
        
    except Exception as e:
        print(f"CRASH during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_pipeline()
