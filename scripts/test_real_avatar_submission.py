import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.getcwd())

from core.agents.avatar_generator import AvatarGenerator

def run_real_test(job_id):
    load_dotenv()
    
    # Paths (adjusting for player/jobs structure)
    job_dir = Path(f"player/jobs/{job_id}")
    pres_path = job_dir / "presentation.json"
    
    if not pres_path.exists():
        print(f"Error: Could not find presentation.json at {pres_path}")
        return

    print(f"--- REAL AVATAR TEST FOR JOB {job_id} ---")
    print(f"Loading presentation from: {pres_path}")
    
    with open(pres_path, "r", encoding="utf-8") as f:
        presentation = json.load(f)
    
    # Expand to sections 1-9 for comprehensive test (Skip exists, Submit missing 7)
    original_sections = presentation.get("sections", [])
    test_ids = [str(i) for i in range(1, 10)]
    test_sections = [s for s in original_sections if str(s.get("section_id")) in test_ids]
    
    if not test_sections:
        print("No sections 1 or 2 found. Using first 2 sections regardless of ID.")
        test_sections = original_sections[:2]
        
    presentation["sections"] = test_sections
    print(f"Selected {len(test_sections)} sections for testing.")
    for s in test_sections:
        print(f"  - Sec {s.get('section_id')}: {s.get('narration_segments', [{}])[0].get('text', '')[:50]}...")

    # Initialize REAL generator
    try:
        generator = AvatarGenerator()
        print(f"API URL: {generator.api_url}")
        
        # Call the REAL submit_all_jobs function
        results = generator.submit_all_jobs(
            presentation=presentation,
            job_id=job_id,
            output_dir=str(job_dir)
        )
        
        print("\n--- SUBMISSION RESULTS ---")
        print(json.dumps(results, indent=2))
        
        analysis_path = job_dir / "avatar_analysis.json"
        if analysis_path.exists():
            print(f"\nSUCCESS: Created {analysis_path}")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    jid = "48808436"
    if len(sys.argv) > 1:
        jid = sys.argv[1]
    run_real_test(jid)
