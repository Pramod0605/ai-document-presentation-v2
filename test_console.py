import requests
import os

url = "http://localhost:5000/submit_job"
file_path = r"c:/Users/email/Downloads/AI-Document-presentation/ai-doc-presentation/attached_assets/Biology_M-23-Chapter_1765713024063.pdf"

files = {'file': open(file_path, 'rb')}
data = {
    'subject': 'Biology Console Test',
    'grade': '10',
    'dry_run': 'false', # Need real run to see WAN info
    'skip_wan': 'false',
    'pipeline_version': 'v15_v2_director'
}

print(f"Submitting job to verify console refinement...")
try:
    response = requests.post(url, files=files, data=data)
    print("Response Status:", response.status_code)
    print("Response Body:", response.json())
except Exception as e:
    print("Error:", e)
