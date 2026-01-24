import requests

job_id = "3407350e"
url = f"http://localhost:5005/assets/{job_id}/presentation.json"

try:
    r = requests.head(url)
    print(f"Status for {url}: {r.status_code}")
except Exception as e:
    print(f"Error: {e}")
