import sys
import os
import traceback

# Add root to sys.path
sys.path.append(os.getcwd())

print("--- DIAGNOSTIC START ---")

try:
    print("1. Importing JobCertifier...")
    from core.validators.job_certifier import JobCertifier
    print("   ✅ Success")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    traceback.print_exc()

try:
    print("2. Importing pipeline_unified...")
    import core.pipeline_unified
    print("   ✅ Success")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    traceback.print_exc()

print("--- DIAGNOSTIC END ---")
