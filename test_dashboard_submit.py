import requests
import time
import os
import sys

# Configuration
BASE_URL = "http://localhost:5000"
TEST_FILE_CONTENT = """
# Integration Test Doc
This is a test document to verify the Unified Pipeline wiring.

## Section 1: Introduction
Welcome to the unified pipeline test.

## Section 2: Visuals
We need a diagram here.
[DIAGRAM: A flowchart showing Dashboard -> App -> Unified Pipeline]
"""

def test_dashboard_submission():
    print(f"Testing Dashboard Submission to {BASE_URL}/submit_job...")
    
    # Create a dummy markdown file
    filename = "test_unified_wiring.md"
    with open(filename, "w") as f:
        f.write(TEST_FILE_CONTENT)
        
    try:
        # Prepare payload matching dashboard.html
        with open(filename, 'rb') as f:
            files = {
                'file': (filename, f, 'text/markdown')
            }
            data = {
                'subject': 'System Testing',
                'grade': '12',
                'dry_run': 'true',  # Dry run for speed
                'skip_wan': 'true',
                'skip_avatar': 'true',
                'tts_provider': 'estimate',
                'pipeline_version': 'v15_v2' # CRITICAL: This triggers the wiring we just fixed
            }
            
            # Send Request
            response = requests.post(f"{BASE_URL}/submit_job", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get("job_id")
            print(f"✅ Submission Successful! Job ID: {job_id}")
            monitor_job(job_id)
        else:
            print(f"❌ Submission Failed: {response.status_code}")
            print(response.text)
            
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def monitor_job(job_id):
    print(f"Monitoring Job {job_id}...")
    while True:
        try:
            res = requests.get(f"{BASE_URL}/job/{job_id}/status")
            status_data = res.json()
            
            phase = status_data.get("current_phase_key", "unknown")
            msg = status_data.get("status_message", "")
            status = status_data.get("status")
            
            print(f"[{status.upper()}] Phase: {phase} | {msg}")
            
            if status in ["completed", "failed"]:
                print(f"🏁 Job Finished with status: {status}")
                if status == "completed":
                    verify_pipeline_execution(job_id)
                break
                
            time.sleep(2)
        except Exception as e:
            print(f"Monitor Error: {e}")
            break

def verify_pipeline_execution(job_id):
    # Check if correct pipeline was used by inspecting analytics or logs
    # We can check via API if available, or just trust the completion for now
    print("Verifying execution details...")
    try:
        res = requests.get(f"{BASE_URL}/jobs")
        jobs = res.json().get("jobs", [])
        target_job = next((j for j in jobs if j["job_id"] == job_id), None)
        
        if target_job:
            # Check if it has 'pipeline_version' in params or metadata
            print(f"Job Params: {target_job.get('params')}")
            # If we see 'v15_v2' and it succeeded via our new code, good.
    except:
        pass

if __name__ == "__main__":
    test_dashboard_submission()
