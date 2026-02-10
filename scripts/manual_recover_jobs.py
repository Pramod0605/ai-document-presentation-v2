import json
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='[RECOVERY] %(message)s')
logger = logging.getLogger(__name__)

# Constants
JOBS_DIR = Path("player/jobs")
JOBS_INDEX_FILE = JOBS_DIR / "jobs_index.json"

TARGET_JOBS = ["71694fdf", "3ef0a373", "7447d348"]

def recover_jobs():
    if not JOBS_INDEX_FILE.exists():
        logger.error(f"Jobs index file not found at {JOBS_INDEX_FILE}")
        return

    try:
        with open(JOBS_INDEX_FILE, 'r') as f:
            jobs_data = json.load(f)
            
        jobs_index = jobs_data.get("jobs", {}) # Structure check needed? Usually Dict[str, dict] directly or {"jobs": ...}
        
        # Check structure - JobManager.load_jobs_index usually returns Dict[str, dict]
        # But if it saves as {"jobs": ...}, we need to handle that.
        # Looking at JobManager code: self._jobs = load_jobs_index()
        # and persist does: json.dump(self._jobs, f) -> So it's likely a direct Dict
        
        if "jobs" in jobs_data and isinstance(jobs_data["jobs"], dict):
             target_dict = jobs_data["jobs"]
             is_nested = True
        else:
             target_dict = jobs_data
             is_nested = False
             
        changed = False
        
        for job_id in TARGET_JOBS:
            if job_id in target_dict:
                job = target_dict[job_id]
                job_dir = JOBS_DIR / job_id
                pres_path = job_dir / "presentation.json"
                
                if pres_path.exists():
                    logger.info(f"Recovering Job {job_id}...")
                    job["status"] = "completed_with_errors"
                    job["error"] = None
                    job["status_message"] = "Manually Recovered. Ready for Retry."
                    job["failure_message"] = "Job recovered from auto-fail. Please retry specific assets."
                    changed = True
                else:
                    logger.warning(f"Job {job_id} has no presentation.json. Cannot recover.")
            else:
                logger.warning(f"Job {job_id} not found in index.")
        
        if changed:
            # Backup first
            backup_path = JOBS_INDEX_FILE.with_suffix(".json.bak")
            with open(backup_path, 'w') as f:
                json.dump(jobs_data, f, indent=4)
            logger.info(f"Backed up index to {backup_path}")
            
            with open(JOBS_INDEX_FILE, 'w') as f:
                json.dump(jobs_data, f, indent=4)
            logger.info("Successfully updated jobs index.")
        else:
            logger.info("No jobs needed recovery.")

    except Exception as e:
        logger.error(f"Recovery failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    recover_jobs()
