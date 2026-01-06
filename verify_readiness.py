import os
import sys
from dotenv import load_dotenv

# Ensure we can import from core
sys.path.insert(0, os.getcwd())

# 1. Load Env (Explicitly force .env)
print("Forcing load of .env file...")
load_dotenv(dotenv_path=".env", override=True)

print(f"--- READINESS CHECK (Using core/llm_config.py) ---")
try:
    from core.llm_config import validate_model_access, get_model_name, get_api_key
    
    model = get_model_name()
    key = get_api_key()
    
    print(f"Model Configured: {model}")
    print(f"Key Configured: {key[:10]}...{key[-5:] if key else ''} (Len: {len(key) if key else 0})")
    
    print("Running validate_model_access()...")
    is_valid, message = validate_model_access()
    
    if is_valid:
        print(f"✅ SUCCESS: {message}")
    else:
        print(f"❌ FAILED: {message}")
        
except Exception as e:
    import traceback
    print(f"EXCEPTION: {e}")
    traceback.print_exc()
