import os
import requests
import json
from dotenv import load_dotenv

# 1. Load Env
load_dotenv()
api_key = os.environ.get("OPENROUTER_API_KEY")
# STRICTLY USE ENV MODEL (User Requested)
model = os.environ.get("OPENROUTER_MODEL")

if not model:
    print("WARNING: OPENROUTER_MODEL not found in .env, defaulting")
    model = "google/gemini-2.0-flash-exp:free"

print(f"--- AUTH TEST DIAGNOSTIC ---")
print(f"Loading .env from: {os.getcwd()}")
if api_key:
    print(f"API Key Found: {api_key[:10]}... (Length: {len(api_key)})")
else:
    print("CRITICAL: API Key NOT found in os.environ")

print(f"Target Model: {model}")

# 2. Test Request
url = "https://openrouter.ai/api/v1/chat/completions"
# EXACT HEADERS FROM core/llm_config.py
headers = {
    "Authorization": f"Bearer {api_key.strip() if api_key else ''}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://replit.com", 
    "X-Title": "AI Education V2"
}
data = {
    "model": model.strip() if model else "google/gemini-2.5-pro",
    "messages": [
        {"role": "user", "content": "Say hello"}
    ],
    "max_tokens": 5
}

try:
    print(f"--- DEBUG INFO ---")
    print(f"URL: {url}")
    print(f"Model: {data['model']}")
    print(f"Headers[HTTP-Referer]: {headers['HTTP-Referer']}")
    print(f"API Key (Trimmed): {headers['Authorization'][:15]}...{headers['Authorization'][-5:]} (Len: {len(headers['Authorization'])})")
    
    print(f"Sending request...")
    resp = requests.post(url, headers=headers, json=data, timeout=10)
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response Headers: {dict(resp.headers)}")
    print(f"Response Body: {resp.text}")

except Exception as e:
    print(f"EXCEPTION: {e}")
