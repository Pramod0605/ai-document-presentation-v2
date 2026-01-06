
import requests
import time
import os

API_URL = "http://localhost:5000/submit_job"
FILE_PATH = "test_input_v25.md"

def trigger_dry_run():
    if not os.path.exists(FILE_PATH):
        print(f"❌ File {FILE_PATH} not found!")
        return

    print(f"🚀 Submitting {FILE_PATH} for V2.5 DRY RUN...")
    
    with open(FILE_PATH, "rb") as f:
        files = {"file": f}
        data = {
            "pipeline_version": "v15_v2_director",
            "dry_run": "true",
            "subject": "Physics",
            "grade": "10"
        }
        
        try:
            response = requests.post(API_URL, files=files, data=data)
            if response.status_code == 200:
                print("✅ Job Submitted Successfully!")
                print(response.json())
            else:
                print(f"❌ Submission Failed: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    trigger_dry_run()
