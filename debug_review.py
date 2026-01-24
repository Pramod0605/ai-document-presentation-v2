
import requests
import json

try:
    response = requests.get("http://localhost:5005/job/1cd6d75c/presentation_for_review")
    if response.status_code == 200:
        data = response.json()
        sections = data.get("sections", [])
        print(f"Found {len(sections)} sections.")
        for sec in sections:
            print(f"\n--- Section {sec.get('section_id')} ---")
            print(f"VISUAL DESCRIPTION: {sec.get('visual_description')}")
    else:
        print(f"Error: {response.status_code}")
except Exception as e:
    print(f"Exception: {e}")
