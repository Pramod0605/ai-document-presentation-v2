import requests
import time
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:5000"

def submit_test_job(index):
    print(f"Submitting job {index}...")
    # Use a simple markdown content for speed
    markdown = f"# Test Presentation {index}\n\nThis is a quick test for parallel execution. Section {index} is being processed."
    
    response = requests.post(f"{BASE_URL}/submit_job", json={
        "markdown": markdown,
        "subject": "Parallel Test",
        "grade": "10",
        "dry_run": True, # Use dry_run=True to avoid long LLM/rendering calls during basic test
        "tts_provider": "edge"
    })
    
    if response.status_code == 200:
        job_id = response.json().get("job_id")
        print(f"Job {index} accepted: {job_id}")
        return job_id
    else:
        print(f"Job {index} failed: {response.status_code} - {response.text}")
        return None

def main():
    print("Testing Parallel Job Submission...")
    
    # Check health first
    try:
        requests.get(f"{BASE_URL}/health")
    except Exception:
        print(f"Error: API not reachable at {BASE_URL}. Is it running?")
        return

    # Submit 3 jobs in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        job_ids = list(executor.map(submit_test_job, range(1, 4)))
    
    # Filter out failed submissions
    job_ids = [jid for jid in job_ids if jid]
    
    if not job_ids:
        print("No jobs were submitted successfully.")
        return

    print("\nMonitoring parallel jobs...")
    for _ in range(5): # Check for a minute or so
        response = requests.get(f"{BASE_URL}/jobs")
        if response.status_code == 200:
            jobs = response.json().get("jobs", [])
            processing_jobs = [j for j in jobs if j["status"] == "processing"]
            print(f"Active processing jobs: {len(processing_jobs)}")
            for pj in processing_jobs:
                print(f"  - Job {pj['job_id']}: {pj.get('status_message', 'Starting...')}")
        
        if not any(j["status"] == "processing" for j in jobs):
            print("All test jobs completed/failed.")
            break
            
        time.sleep(5)

if __name__ == "__main__":
    main()
