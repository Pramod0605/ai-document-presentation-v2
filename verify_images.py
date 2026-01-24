import requests
import logging

logging.basicConfig(level=logging.INFO)

job_id = "3407350e"
img_id_base = "c803f6f6e2c49429d2951832bd0f208d_img"
# Test both jpg and png extensions
paths = [
    f"/player/jobs/{job_id}/images/{img_id_base}.png",
    f"/player/jobs/{job_id}/images/{img_id_base}.jpg"
]

for path in paths:
    url = f"http://localhost:5005{path}"
    try:
        r = requests.head(url)
        print(f"{path}: {r.status_code}")
    except Exception as e:
        print(f"{path}: Error {e}")
