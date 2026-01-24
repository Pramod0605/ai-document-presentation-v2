import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Test with job 1cd6d75c (or any available job)
job_id = "1cd6d75c" 
url = f"http://localhost:5005/job/{job_id}/presentation_for_review"

try:
    logging.info(f"Fetching data from {url}")
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    sections = data.get('sections', [])
    logging.info(f"Retrieved {len(sections)} sections")
    
    for section in sections:
        content = section.get('content', {})
        sid = section.get('section_id')
        title = section.get('title')
        
        # Check Explanation Plan
        plan = content.get('explanation_plan')
        if plan and isinstance(plan, str) and (plan.startswith('{') or plan.startswith('[')):
            logging.info(f"Section {sid} ({title}): Explanation Plan is a JSON string (GOOD)")
        elif plan and plan == "[object Object]":
             logging.error(f"Section {sid} ({title}): Explanation Plan is [object Object] (BAD)")
             
        # Check Visual Beats
        beats = content.get('visual_beats', [])
        if beats:
            logging.info(f"Section {sid} ({title}): Found {len(beats)} visual beats")
            for b in beats[:1]:
                desc = b.get('description')
                if desc:
                    logging.info(f"  - Beat sample: {desc[:50]}...")
                else:
                    logging.warning(f"  - Beat has empty description!")
                    
        # Check Bullets
        bullets = content.get('bullet_items', [])
        if bullets:
             logging.info(f"Section {sid} ({title}): Found {len(bullets)} bullet items")
             
        # Check Images
        images = content.get('images', [])
        if images:
             logging.info(f"Section {sid} ({title}): Found {len(images)} images")

except Exception as e:
    logging.error(f"Test failed: {e}")
