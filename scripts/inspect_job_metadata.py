import json
from pathlib import Path

JOB_ID = "f3c9afc7"
INDEX_PATH = Path("player/jobs/jobs_index.json")

def inspect_metadata():
    if not INDEX_PATH.exists():
        print("❌ jobs_index.json NOT FOUND")
        return
        
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        jobs = data.get("jobs", {})
        job = jobs.get(JOB_ID)
        
        if not job:
            print(f"❌ Job {JOB_ID} not found in index")
            return
            
        print(f"✅ Found Job {JOB_ID} metadata:")
        print(json.dumps(job, indent=2))
        
        pv = job.get("pipeline_version")
        print(f"\nPipeline Version: '{pv}'")
        
        if pv == "v15_v2_director":
             print("✅ Metadata confirms Director Mode selected.")
        else:
             print("❌ Metadata indicates WRONG version.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_metadata()
