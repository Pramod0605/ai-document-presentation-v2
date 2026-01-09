import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load .env
load_dotenv()

api_url = os.environ.get("AVATAR_API_URL")
if not api_url:
    print("Error: AVATAR_API_URL not set in .env")
    sys.exit(1)

def check_and_download(task_id):
    print(f"Checking Task: {task_id}")
    try:
        # Check Status
        status_url = f"{api_url}/status/{task_id}"
        resp = requests.get(status_url, timeout=10)
        
        if resp.status_code != 200:
            print(f"Error checking status: {resp.status_code}")
            return

        data = resp.json()
        print(json.dumps(data, indent=2))
        
        # Check if completed
        # Live API returns "status" at root
        if "task_status" in data:
             status = data["task_status"].get("status")
        else:
             status = data.get("status")
        
        if status == "completed":
            # Extract URL
            download_url = None
            # Check deep nesting: result -> data -> result_url
            res_block = data.get("result", {})
            if isinstance(res_block, dict):
                 inner_data = res_block.get("data", {})
                 if isinstance(inner_data, dict) and "result_url" in inner_data:
                      rel_url = inner_data["result_url"]
                      # Construct absolute URL
                      base = api_url.replace("/api", "")
                      download_url = f"{base}{rel_url}"

            if not download_url:
                 # Fallback
                 download_url = f"{api_url}/download/{task_id}"

            print(f"\nStatus is COMPLETED. Downloading from {download_url}...")
            output_file = f"{task_id}.mp4"
            
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(output_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            print(f"Saved to {os.path.abspath(output_file)}")
        else:
            print(f"\nTask not ready yet. Status: {status}")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_avatar_task.py <task_id>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    check_and_download(task_id)
