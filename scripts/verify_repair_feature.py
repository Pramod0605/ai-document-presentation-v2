
import requests
import os
import shutil
from pathlib import Path
import json

API_BASE_URL = "http://localhost:5000"
JOBS_DIR_PATH = Path("jobs") # Assuming running from repo root

def get_job_with_avatar():
    # 1. Find a job with a completed avatar
    try:
        resp = requests.get(f"{API_BASE_URL}/jobs")
        jobs = resp.json().get("jobs", [])
        
        for job in jobs:
            jid = job["job_id"]
            # Check presentation.json for avatar
            # Since we can't easily peek inside without auth/local access, let's try to hit the file endpoint
            # Actually, let's just use the repair endpoint to 'scan' for us.
            # If it returns "exists", we know it has one.
            pass
            
            # Alternative: check local folder if available
            job_folder = JOBS_DIR_PATH / jid
            pres_path = job_folder / "presentation.json"
            if pres_path.exists():
                with open(pres_path, "r") as f:
                    data = json.load(f)
                    for sec in data.get("sections", []):
                        if sec.get("avatar_task_id") and sec.get("avatar_status") == "completed":
                            return jid, sec.get("section_id"), sec.get("avatar_video")
                            
    except Exception as e:
        print(f"Error finding job: {e}")
    return None, None, None

def verify_repair():
    print("--- Verifying Asset Auto-Repair ---")
    
    # 1. Identify a target
    job_id, sec_id, avatar_rel_path = get_job_with_avatar()
    if not job_id:
        print("Test Skipped: No completed avatars found to test with.")
        return

    print(f"Target Job: {job_id}, Section: {sec_id}")
    print(f"Avatar: {avatar_rel_path}")
    
    full_path = JOBS_DIR_PATH / job_id / avatar_rel_path
    
    # 2. Simulate Data Loss
    if full_path.exists():
        backup_path = full_path.with_suffix(".mp4.bak")
        shutil.move(str(full_path), str(backup_path))
        print(f"Action: Moved avatar to {backup_path} (Simulating loss)")
    else:
        print("Error: Target avatar file not found on disk!")
        return

    # 3. Call Repair
    print("Action: Calling /api/repair-missing-assets...")
    resp = requests.post(f"{API_BASE_URL}/api/repair-missing-assets/{job_id}")
    result = resp.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    # 4. Verify Restoration
    if full_path.exists():
        print("SUCCESS: Avatar file restored!")
        # Clean up backup
        if backup_path.exists():
             os.remove(backup_path)
    else:
        print("FAILURE: Avatar file NOT restored.")
        # Restore backup manually
        if backup_path.exists():
             shutil.move(str(backup_path), str(full_path))

if __name__ == "__main__":
    verify_repair()
