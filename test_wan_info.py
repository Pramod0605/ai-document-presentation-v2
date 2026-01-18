import requests
import os

url = "http://localhost:5000/submit_job"
markdown_content = """# Intro
Hello.
# Scientific Concept
This is a scientific concept that needs WAN video.
@@renderer: video
@@video: A simple botanical demonstration of vegetative propagation.
"""

payload = {
    'subject': 'WAN Test',
    'grade': '10',
    'dry_run': 'false',
    'skip_wan': 'false',
    'pipeline_version': 'v15_v2_director',
    'markdown': markdown_content
}

print(f"Submitting small markdown job to verify WAN info (via JSON)...")
try:
    response = requests.post(url, json=payload)
    print("Response Status:", response.status_code)
    print("Response Body:", response.json())
except Exception as e:
    print("Error:", e)
