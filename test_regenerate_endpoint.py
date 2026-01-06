"""
Test calling the regenerate_manim endpoint
Run this AFTER you add the endpoint to app.py
"""
import requests

JOB_ID = "d76a0cc1"
URL = f"http://localhost:5000/regenerate_manim/{JOB_ID}"

print(f"Triggering Manim regeneration for job {JOB_ID}...")
print(f"POST {URL}\n")

try:
    response = requests.post(URL, timeout=300)  # 5 minute timeout for LLM calls
    
    if response.status_code == 200:
        result = response.json()
        print("✅ SUCCESS!")
        print(f"\nGenerated: {len(result['results']['generated'])} sections")
        print(f"Failed: {len(result['results']['failed'])} sections")
        
        for item in result['results']['generated']:
            print(f"  ✓ Section {item['section_id']}: {item['title']} ({item['code_length']} chars, {item['segments']} segments)")
        
        if result['results']['failed']:
            print("\nFailed sections:")
            for item in result['results']['failed']:
                print(f"  ✗ Section {item['section_id']}: {item['error']}")
    else:
        print(f"❌ ERROR {response.status_code}")
        print(response.text)
        
except requests.exceptions.ConnectionError:
    print("❌ Could not connect to server")
    print("Make sure api/app.py is running")
except Exception as e:
    print(f"❌ Error: {e}")
