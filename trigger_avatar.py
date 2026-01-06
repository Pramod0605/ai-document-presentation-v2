"""
Trigger Avatar Generation for Job d76a0cc1
"""
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from core.agents.avatar_generator import AvatarGenerator

JOB_ID = "d76a0cc1"
JOB_DIR = Path(f"player/jobs/{JOB_ID}")

def trigger_avatar():
    print(f"=" * 60)
    print(f"AVATAR GENERATION FOR JOB {JOB_ID}")
    print(f"=" * 60)
    
    # Load presentation
    pres_path = JOB_DIR / "presentation.json"
    with open(pres_path, "r", encoding="utf-8") as f:
        presentation = json.load(f)
    
    sections = presentation.get("sections", [])
    print(f"\nLoaded {len(sections)} sections")
    
    # Submit Avatar Generation
    print("\nSubmitting to Avatar API...")
    avatar_gen = AvatarGenerator()
    results = avatar_gen.submit_parallel_job(presentation, JOB_ID, str(JOB_DIR))
    
    print(f"\n✅ Avatar Generation Submitted!")
    print(f"   Queued: {len(results['queued'])}")
    print(f"   Skipped: {len(results['skipped'])}")
    print(f"   Failed: {len(results['failed'])}")
    
    if results['queued']:
        print(f"\n📝 Avatar videos will be generated in background")
        print(f"   Check: player/jobs/{JOB_ID}/avatar_status.json")

if __name__ == "__main__":
    trigger_avatar()
