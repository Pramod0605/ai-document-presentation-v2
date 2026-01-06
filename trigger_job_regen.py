import json
import requests
import sys
import os

JOB_ID = "603bd693"
JSON_PATH = f"player/jobs/{JOB_ID}/presentation.json"
API_URL = f"http://localhost:5005/job/{JOB_ID}/retry_phase"

def main():
    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} not found")
        sys.exit(1)

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    manim_sections = []
    for section in data.get("sections", []):
        if section.get("renderer") == "manim":
            manim_sections.append(section.get("section_id"))

    if not manim_sections:
        print("No Manim sections found.")
        sys.exit(0)

    print(f"Found Manim sections: {manim_sections}")
    
    # Process sequentially to avoid timeouts
    for sec_id in manim_sections:
        print(f"\n[SECTION {sec_id}] Triggering Regeneration...")
        payload = {
            "phase": "manim_codegen",
            "section_ids": [sec_id]
        }
        try:
            resp = requests.post(API_URL, json=payload, timeout=300) # 5 min timeout per section
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"Success: {json.dumps(resp.json(), indent=2)}")
            else:
                print(f"Failed: {resp.text}")
        except Exception as e:
            print(f"Exception during request for Section {sec_id}: {e}")

    # 2. Render Videos (Video Render)
    # Optional: User might want to check code first, but usually they want results.
    # We will just do codegen first to be safe and verified.

if __name__ == "__main__":
    main()
