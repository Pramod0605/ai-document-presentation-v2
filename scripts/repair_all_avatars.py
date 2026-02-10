
import os
import sys
import requests
import time
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:5000"
JOBS_DIR = Path("C:/Users/Administrator/Desktop/ai-doc-presentation/jobs") 
# Note: Adjust JOBS_DIR if running locally vs server. 
# Better to use the API to list jobs if possible, but we don't have a list-all-ids endpoint easily accessible without auth potentially.
# Let's rely on the user running this from the repo root mostly.

def repair_all_jobs():
    print(f"--- Asset Auto-Repair Tool ---")
    print(f"Target API: {API_BASE_URL}")
    
    # 1. Get all jobs from API (more reliable than scanning disk if API is running)
    try:
        resp = requests.get(f"{API_BASE_URL}/jobs")
        if resp.status_code != 200:
            print(f"Matches error: Failed to list jobs. {resp.text}")
            return
            
        data = resp.json()
        jobs = data.get("jobs", [])
        print(f"Found {len(jobs)} jobs in history.")
        
    except Exception as e:
        print(f"Error connecting to API: {e}")
        print("Ensure server is running on localhost:5000")
        return

    # 2. Iterate and Repair
    repaired_total = 0
    failed_total = 0
    
    for job in jobs:
        job_id = job.get("job_id")
        print(f"\n[Job {job_id}] Checking...", end="")
        
        try:
            # Call the new repair endpoint
            r_resp = requests.post(f"{API_BASE_URL}/api/repair-missing-assets/{job_id}", timeout=60)
            
            if r_resp.status_code == 200:
                r_data = r_resp.json()
                count = r_data.get("repaired_count", 0)
                details = r_data.get("details", [])
                
                if count > 0:
                    print(f" REPAIRED {count} assets!")
                    for d in details:
                        if d.get("status") == "repaired":
                            print(f"  - Sec {d['section_id']} ({d['type']}): Restored")
                    repaired_total += count
                else:
                    # Check if any failed
                    failures = [d for d in details if d.get("status") == "failed"]
                    if failures:
                        print(f" Issues found ({len(failures)} unrecoverable).")
                        for f in failures:
                            print(f"  - Sec {f['section_id']}: {f.get('reason')}")
                    else:
                        print(" OK (All assets present)")
            else:
                print(f" Failed to check. Status: {r_resp.status_code}")
                
        except Exception as e:
            print(f" Exception: {e}")
            
    print(f"\n--- Summary ---")
    print(f"Total Repaired Assets: {repaired_total}")
    print(f"Run 'sanity_check.html?job=<job_id>' to verify individual jobs.")

if __name__ == "__main__":
    repair_all_jobs()
