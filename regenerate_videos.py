"""
Regenerate videos for an existing job using V2.5 pipeline.
Supports parallel execution for WAN and Manim videos.

Usage: python regenerate_videos.py <JOB_ID>
"""
import sys
import json
import logging
import concurrent.futures
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load env (for API keys)
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.renderer_executor import execute_renderer

def regenerate_videos(job_id: str):
    job_dir = Path(f"player/jobs/{job_id}")
    pres_file = job_dir / "presentation.json"
    
    if not pres_file.exists():
        logger.error(f"Job not found: {job_id}")
        return

    logger.info(f"Loading job {job_id}...")
    with open(pres_file, 'r', encoding='utf-8') as f:
        presentation = json.load(f)
        
    sections = presentation.get("sections", [])
    output_dir = job_dir / "videos"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    tasks = []
    
    # Identify video tasks
    for section in sections:
        renderer = section.get("visual", {}).get("renderer", "none")
        # Also check top level if synced
        if renderer == "none":
            renderer = section.get("renderer", "none")
            
        if renderer in ["wan_video", "manim_flow", "manim_video", "video"]:
            tasks.append(section)

    logger.info(f"Found {len(tasks)} video tasks to render.")
    
    if not tasks:
        logger.warning("No video sections found. Did you run patch_job_json.py first?")
        return

    # Run in parallel
    MAX_WORKERS = 3  # Validated safe limit
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_section = {
            executor.submit(
                execute_renderer, 
                topic=section, 
                output_dir=str(output_dir), 
                dry_run=False
            ): section for section in tasks
        }
        
        for future in concurrent.futures.as_completed(future_to_section):
            section = future_to_section[future]
            try:
                result = future.result()
                results.append(result)
                status = result.get("status", "unknown")
                logger.info(f"[Render] Section {section.get('section_id')}: {status}")
            except Exception as e:
                logger.error(f"[Render] Section {section.get('section_id')} Failed: {e}")

    logger.info("Regeneration complete!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python regenerate_videos.py <JOB_ID>")
        sys.exit(1)
    
    regenerate_videos(sys.argv[1])
