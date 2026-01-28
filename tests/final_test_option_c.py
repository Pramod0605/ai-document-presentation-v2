"""
Final test for Option C - Default pipeline with validator
"""
import requests
import json
import time
from pathlib import Path

print("=" * 80)
print("FINAL TEST - Option C Implementation")
print("Testing default pipeline now uses validator path")
print("=" * 80)

test_file = Path("tests/test_pythagorean.md")
print(f"\n✓ Test file: {test_file}")

# Submit job WITHOUT specifying pipeline_version (use default)
print("\n[1/3] Submitting job with DEFAULT pipeline...")
try:
    with open(test_file, 'rb') as f:
        files = {'file': ('test_pythagorean.md', f, 'text/markdown')}
        data = {
            'subject': 'Mathematics',
            'grade': '9',
            'dry_run': 'true',
            'skip_wan': 'true'
            # NOTE: NOT specifying pipeline_version - should use default
        }
        
        response = requests.post('http://localhost:5000/submit_job', files=files, data=data)
        result = response.json()
        
        if response.status_code == 200:
            job_id = result['job_id']
            print(f"✓ Job submitted: {job_id}")
            print(f"  Using DEFAULT pipeline (should be v15_v2_director)")
        else:
            print(f"✗ Failed: {result}")
            exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)

# Monitor
print(f"\n[2/3] Monitoring job {job_id}...")
start_time = time.time()
while time.time() - start_time < 120:
    try:
        response = requests.get(f'http://localhost:5000/job/{job_id}/status')
        status_data = response.json()
        status = status_data['status']
        
        if status == 'completed':
            print(f"✓ Job completed in {int(time.time() - start_time)}s")
            break
        elif status == 'failed':
            print(f"✗ Job failed: {status_data.get('error')}")
            exit(1)
        
        time.sleep(3)
    except:
        time.sleep(3)

# Check validator artifacts
print(f"\n[3/3] Checking Content Completeness Validator...")
job_dir = Path(f"player/jobs/{job_id}")
artifacts_dir = job_dir / "artifacts"
validation_file = artifacts_dir / "completeness_validation.json"

print(f"\n{'='*80}")
print("VALIDATION RESULTS")
print(f"{'='*80}")

if validation_file.exists():
    print(f"\n✅ SUCCESS! Validator executed!")
    print(f"✓ Validation file: {validation_file}")
    
    with open(validation_file, 'r') as f:
        val_data = json.load(f)
    
    print(f"\nValidation Details:")
    print(f"  Status: {val_data.get('validation_status')}")
    print(f"  Timestamp: {val_data.get('timestamp')}")
    if 'metrics' in val_data:
        metrics = val_data['metrics']
        print(f"\n  Metrics:")
        print(f"    Word count ratio: {metrics.get('word_count_ratio', 'N/A')}")
        print(f"    Topics coverage: {metrics.get('topics_coverage', 'N/A')}")
        print(f"    Images coverage: {metrics.get('images_coverage', 'N/A')}")
    
    # Check presentation metadata
    pres_path = job_dir / "presentation.json"
    if pres_path.exists():
        with open(pres_path, 'r') as f:
            pres = json.load(f)
        
        metadata = pres.get('metadata', {})
        print(f"\nPresentation Metadata:")
        print(f"  Pipeline mode: {metadata.get('pipeline_mode')}")
        print(f"  Validation passed: {metadata.get('validation_passed_first_attempt', False)}")
    
    print(f"\n{'='*80}")
    print("✅ OPTION C: SUCCESSFUL - Validator is working!")
    print(f"{'='*80}")
else:
    print(f"\n✗ FAILED - Validator did not execute")
    print(f"  Validation file not found: {validation_file}")
    print(f"  Artifacts dir exists: {artifacts_dir.exists()}")
    if artifacts_dir.exists():
        files = list(artifacts_dir.glob("*"))
        print(f"  Files in artifacts: {[f.name for f in files]}")
    exit(1)

print(f"\nJob directory: {job_dir}")
print(f"Test completed successfully! ✅")
