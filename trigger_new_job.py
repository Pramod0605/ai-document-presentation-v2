import requests
import json
import time

URL = "http://127.0.0.1:5000/api/v15/generate"

# Simplified context for testing
# We use the text we found earlier for "Shalika" to see if it generates a video prompt
MARKDOWN = """
# Arithmetic Progressions

## Introduction
A sequence is called an Arithmetic Progression (AP) if the difference between any two consecutive terms is always constant.

## Real World Example
Example : Shalika puts 100 rupees into her daughter money box when she was one year old and increased the amount by 50 rupees every year. The amounts of money (in Rs.) in the box on the 1st, 2nd, 3rd, 4th . . . birthday were 100, 150, 200, 250, . . . respectively. This forms an AP.

## Mathematical Formulation
If $a$ is the first term and $d$ is the common difference, then the AP is:
$$a, a+d, a+2d, a+3d, \dots$$

The general term $a_n$ is given by:
$$a_n = a + (n-1)d$$
"""

def submit_job():
    print("Submitting Unified Pipeline Job...")
    try:
        resp = requests.post(URL, json={
            "markdown": MARKDOWN,
            "subject": "Math",
            "grade": "10",
            "skip_wan": True, # Skip heavy rendering for fast verification
            "tts_provider": "estimate" # Fast TTS
        })
        
        if resp.status_code == 200:
            data = resp.json()
            job_id = data.get("job_id")
            ver = data.get("pipeline_version")
            print(f"SUCCESS! Job ID: {job_id}")
            print(f"Pipeline Version: {ver}")
            print(f"Output Path: {data.get('output_path')}")
            
            # Check for Video Prompts
            pres = data.get("presentation", {})
            sections = pres.get("sections", [])
            has_manim = False
            has_wan = False
            
            for s in sections:
                if s.get("renderer") == "manim": has_manim = True
                if s.get("renderer") in ["video", "wan_video"]: has_wan = True
                
            print(f"Has Manim: {has_manim}")
            print(f"Has WAN/Video: {has_wan}")
            
        else:
            print(f"FAILED: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    submit_job()
