import json
import os
import shutil
from pathlib import Path

def cleanup_jobs(jobs_dir_path, index_file_path, keep_count=3):
    jobs_dir = Path(jobs_dir_path)
    index_file = Path(index_file_path)
    
    if not index_file.exists():
        print(f"Index file {index_file} not found.")
        return

    print(f"Loading index from {index_file}...")
    with open(index_file, 'r') as f:
        try:
            jobs = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return

    # Sort jobs by created_at descending
    # Example format: "2025-12-16T08:22:41.254831"
    sorted_job_ids = sorted(
        jobs.keys(),
        key=lambda j: jobs[j].get('created_at', ''),
        reverse=True
    )
    
    keep_ids = set(sorted_job_ids[:keep_count])
    delete_ids = set(sorted_job_ids[keep_count:])
    
    print(f"Keeping {len(keep_ids)} jobs: {list(keep_ids)}")
    print(f"Found {len(delete_ids)} jobs to remove from index.")
    
    # Update index
    new_jobs = {jid: jobs[jid] for jid in keep_ids}
    
    with open(index_file, 'w') as f:
        json.dump(new_jobs, f, indent=2)
    print(f"Updated index saved with {len(new_jobs)} entries.")
    
    # Cleanup directory
    print(f"Checking directory {jobs_dir} for cleanup...")
    for item in jobs_dir.iterdir():
        if item.is_dir() and item.name not in keep_ids:
            print(f"Deleting directory: {item.name}")
            shutil.rmtree(item)
    
    print("Cleanup complete.")

if __name__ == "__main__":
    # BASE_DIR should be the project root
    BASE_DIR = Path(__file__).parent.parent
    JOBS_DIR = BASE_DIR / "player" / "jobs"
    INDEX_FILE = JOBS_DIR / "jobs_index.json"
    cleanup_jobs(JOBS_DIR, INDEX_FILE)
