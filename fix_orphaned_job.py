import json
import sys
import os
from pathlib import Path

def fix_job(job_id):
    index_path = Path("player/jobs/jobs_index.json")
    if not index_path.exists():
        print(f"Error: {index_path} not found.")
        return

    # 1. Update jobs_index.json
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
    except Exception as e:
        print(f"Error reading index: {e}")
        return

    if job_id not in index_data:
        print(f"Error: Job {job_id} not found in index.")
        # Try to find it by scanning folders
        job_dir = Path("player/jobs") / job_id
        if job_dir.exists():
            print(f"Job directory exists at {job_dir}, but not in index. Creating entry...")
            index_data[job_id] = {
                "id": job_id,
                "status": "completed_with_errors",
                "timestamp": os.path.getmtime(job_dir),
                "error": "Orphaned job recovered by script"
            }
        else:
            return

    job_info = index_data[job_id]
    if job_info.get("status") == "processing":
        job_info["status"] = "completed_with_errors"
        job_info["error"] = "Process orphaned or hung during generation. Recovered manualy."
        print(f"Updated index status for {job_id} to completed_with_errors.")
    else:
        print(f"Job {job_id} is already in state: {job_info.get('status')}")

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2)

    # 2. Update presentation.json in job folder
    pres_path = Path("player/jobs") / job_id / "presentation.json"
    if pres_path.exists():
        try:
            with open(pres_path, 'r', encoding='utf-8') as f:
                presentation = json.load(f)
            
            meta = presentation.setdefault("metadata", {})
            meta["job_status"] = "completed_with_errors"
            meta["error_summary"] = "Process orphaned or hung during generation. Recovered manually."
            
            with open(pres_path, 'w', encoding='utf-8') as f:
                json.dump(presentation, f, indent=4)
            print(f"Updated metadata in {pres_path}")
        except Exception as e:
            print(f"Warning: Could not update presentation.json: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_orphaned_job.py <job_id>")
        sys.exit(1)
    
    fix_job(sys.argv[1])
