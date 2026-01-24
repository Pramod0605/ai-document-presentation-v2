
import requests
import json

try:
    # Use the job ID we know works from previous turn
    job_id = "1cd6d75c" 
    url = f"http://localhost:5005/job/{job_id}/presentation_for_review"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"--- FULL DEBUG DUMP FOR JOB {job_id} ---")
        # Dump section 2 specifically
        sections = data.get("sections", [])
        if len(sections) > 1:
            print("\n--- SECTION 2 RAW ---")
            print(json.dumps(sections[1], indent=2))
        else:
            print("\n--- ALL SECTIONS SUMMARY ---")
            for i, s in enumerate(sections):
                print(f"Sec {i+1}: {s.get('title')} - Len Desc: {len(s.get('visual_description', ''))}")
    else:
        print(f"Error: {response.status_code}")
        
    # Also lets try to see what the 'status' endpoint says about the path
    status_url = f"http://localhost:5005/job/{job_id}/status"
    status_resp = requests.get(status_url)
    if status_resp.status_code == 200:
        print("\n--- JOB STATUS ---")
        print(json.dumps(status_resp.json(), indent=2))

except Exception as e:
    print(f"Exception: {e}")
