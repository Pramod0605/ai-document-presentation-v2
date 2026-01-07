
import json
from pathlib import Path

index_path = Path("player/jobs/jobs_index.json")

if not index_path.exists():
    print("No index file found")
    exit(1)

with open(index_path, 'r') as f:
    data = json.load(f)

job_id = "83ad0c3f"
if job_id in data:
    data[job_id]["status"] = "completed_with_errors"
    data[job_id]["error"] = "Manually marked as error by User/Agent"
    # Also update presentation.json if possible (optional but good)
    print(f"Updated job {job_id} status to completed_with_errors")
else:
    print(f"Job {job_id} not found in index")

with open(index_path, 'w') as f:
    json.dump(data, f, indent=2)
