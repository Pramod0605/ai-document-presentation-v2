import requests

job_id = "3407350e"
img = "1517552d07f4a8b389be86af8aff6424_img.png"
url = f"http://localhost:5005/assets/{job_id}/images/{img}"

try:
    r = requests.head(url)
    print(f"Status for {url}: {r.status_code}")
except Exception as e:
    print(f"Error: {e}")
