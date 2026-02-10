
import requests
import json
import time

JOB_ID = "7563e624"
BASE_URL = "http://127.0.0.1:5000"

def test_resume():
    print(f"--- Testing Resume Queue for Job {JOB_ID} ---")
    
    # 1. Check current status
    try:
        status_url = f"{BASE_URL}/jobs/{JOB_ID}/status"
        res = requests.get(status_url)
        if res.status_code == 200:
            print(f"Initial Status: {res.json().get('status')}")
        else:
            print(f"Failed to get status: {res.text}")
    except Exception as e:
        print(f"Error checking status (is server running?): {e}")
        return

    # 2. Trigger Resume
    print(f"\nArguments: from_phase='audio', dry_run=False")
    print("Sending Resume Request...")
    
    try:
        resume_url = f"{BASE_URL}/jobs/{JOB_ID}/resume"
        payload = {
            "from_phase": "audio",
            "dry_run": False
        }
        res = requests.post(resume_url, json=payload)
        
        if res.status_code == 200:
            print(f"Response: {res.json()}")
        else:
            print(f"Resume Failed: {res.status_code} - {res.text}")
            return
            
    except Exception as e:
        print(f"Error triggering resume: {e}")
        return

    # 3. Check Status Again (Should be Queued)
    print("\nChecking Status immediately after resume request...")
    time.sleep(1)
    try:
        res = requests.get(status_url)
        status = res.json().get('status')
        print(f"New Status: {status}")
        
        if status == "queued":
            print("\nSUCCESS: Job successfully queued! (Pipeline limit reached)")
        elif status == "processing":
            print("\nWARNING: Job started processing immediately (Did other jobs finish?)")
        else:
            print(f"\nUnexpected Status: {status}")
            
    except Exception as e:
        print(f"Error checking final status: {e}")

if __name__ == "__main__":
    test_resume()
