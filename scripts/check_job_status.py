import sys
import os
import json

# Add root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.job_manager import job_manager

# Get all jobs and sort by created_at desc
jobs = job_manager.get_all_jobs()

if not jobs:
    print("No jobs found in manager.")
    sys.exit(0)

latest_job = jobs[0]
JOB_ID = latest_job['id']

print(f"Checking Latest Job {JOB_ID}...")
job = latest_job

if job:
    print(f"STATUS: {job.get('status')}")
    print(f"STEP: {job.get('current_step_name')}")
    print(f"MSG: {job.get('status_message')}")
    print(f"ERROR: {job.get('error')}")
    if job.get('result'):
        print("RESULT exists")
else:
    print("Job not found.")
