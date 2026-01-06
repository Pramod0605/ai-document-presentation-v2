import os
import requests
from dotenv import load_dotenv

# Force reload of .env
load_dotenv(override=True)

def verify_key():
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    print("-" * 50)
    print("API KEY DIAGNOSTIC")
    print("-" * 50)
    
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in environment variables.")
        return False
        
    mask = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 15 else "Too Short"
    print(f"✅ Key Found: {mask}")
    
    print("\nTesting Connection to OpenRouter...")
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Connection Successful!")
            print(f"   Key Information: {data}")
            return True
        elif response.status_code == 401:
            print("❌ Authentication Failed (401). The key is invalid.")
            return False
        else:
            print(f"⚠️ API Info Request Failed: {response.status_code} - {response.text}")
            # Try a model list as backup test
            return test_model_list(api_key)
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

def test_model_list(api_key):
    print("\nAttempting to list models as backup verify...")
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        if response.status_code == 200:
            print("✅ Model List Access Successful! (Key works)")
            return True
        else:
            print(f"❌ Model List Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

if __name__ == "__main__":
    verify_key()
