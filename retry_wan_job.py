"""
Retry WAN Video Generation for a specific job (Granular / Fill-in-the-blanks).

This script:
1. Loads the V2.5 presentation.json
2. Invokes the standard V2.5 pipeline component (submit_wan_background_job)
3. RELIES on the enhanced KieBatchGenerator to skip existing files.

Usage:
    python retry_wan_job.py <JOB_ID>
    
Example:
    python retry_wan_job.py d76a0cc1
"""
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup minimal logging to console
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RetryWAN")

# Load environment variables (API keys)
load_dotenv()

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from core.renderer_executor import submit_wan_background_job

def retry_wan_for_job(job_id: str):
    print(f"="*60)
    print(f"RETRY WAN GENERATION: {job_id}")
    print(f"Mode: Granular (Skip existing files)")
    print(f"="*60)
    
    # Locate job
    job_dir = Path(f"player/jobs/{job_id}")
    if not job_dir.exists():
        print(f"❌ Job directory not found: {job_dir}")
        return
        
    pres_path = job_dir / "presentation.json"
    if not pres_path.exists():
        print(f"❌ presentation.json not found: {pres_path}")
        return
        
    # Load presentation
    try:
        with open(pres_path, "r", encoding="utf-8") as f:
            presentation = json.load(f)
            print(f"✅ Loaded presentation with {len(presentation.get('sections', []))} sections")
    except Exception as e:
        print(f"❌ Failed to load presentation: {e}")
        return

    # Trigger V2.5 WAN Pipeline
    # The submit_wan_background_job function handles:
    # - Identifying WAN sections/beats
    # - Batching them
    # - Calling KieBatchGenerator (which now skips existing files!)
    # - Updating presentation.json with results
    try:
        submit_wan_background_job(
            presentation=presentation,
            output_dir=str(job_dir / "videos"),
            job_id=job_id,
            skip_wan=False,
            video_provider="kie"  # Default to Kie for retries
        )
        print("\n✅ Granular retry complete. Check logs above for 'Skipping existing...' messages.")
        
    except Exception as e:
        print(f"\n❌ Retry failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python retry_wan_job.py <JOB_ID>")
        print("Tip: To regenerate a specific beat, delete its .mp4 file before running this.")
        sys.exit(1)
    
    job_id = sys.argv[1]
    retry_wan_for_job(job_id)
