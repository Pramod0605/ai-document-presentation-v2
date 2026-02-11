
import json
import requests
import time

def check_blueprint_status(job_id):
    """
    Polls the job status to check if 'blueprint_ready' flag is True.
    """
    url = f"http://localhost:5000/api/job_status/{job_id}"
    
    print(f"Monitoring Job {job_id} for Blueprint Ready status...")
    
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                blueprint_ready = data.get("blueprint_ready", False)
                status = data.get("status", "unknown")
                step = data.get("current_step_name", "")
                
                print(f"Status: {status} | Step: {step} | Blueprint Ready: {blueprint_ready}")
                
                if blueprint_ready:
                    print("\n✅ BLUEPRINT IS READY!")
                    print("The frontend should now be able to load 'presentation.json' even while rendering continues.")
                    return True
                
                if status in ["completed", "failed", "completed_with_errors"]:
                    print(f"\nJob finished with status: {status}")
                    return False
                    
            else:
                print(f"Error: {response.status_code}")
                
        except Exception as e:
            print(f"Request failed: {e}")
            
        time.sleep(2)

if __name__ == "__main__":
    # You can pass a job ID here to test
    job_id = input("Enter Job ID to monitor: ").strip()
    if job_id:
        check_blueprint_status(job_id)
