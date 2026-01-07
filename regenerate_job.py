"""
Regenerate presentation from source markdown for an existing job.
This re-runs the LLM generation while preserving the job ID.

Usage: python regenerate_job.py <JOB_ID>
"""
import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.pipeline_unified import process_markdown_unified

def regenerate_job(job_id: str):
    """Regenerate presentation from source markdown."""
    job_dir = Path(f"player/jobs/{job_id}")
    md_file = job_dir / "source_markdown.md"
    pres_file = job_dir / "presentation.json"
    
    print("=" * 60)
    print(f"REGENERATING JOB: {job_id}")
    print("=" * 60)
    
    # Check source exists
    if not md_file.exists():
        print(f"❌ Source markdown not found: {md_file}")
        return None
    
    # Load source markdown
    with open(md_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    print(f"✓ Source markdown: {len(markdown_content):,} chars")
    
    # Load existing presentation for metadata
    old_metadata = {}
    if pres_file.exists():
        with open(pres_file, 'r', encoding='utf-8') as f:
            old_pres = json.load(f)
            old_metadata = old_pres.get("metadata", {})
        print(f"✓ Existing presentation: {pres_file.stat().st_size:,} bytes")
        
        # Backup old presentation
        backup_file = job_dir / "presentation_backup.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(old_pres, f, indent=2)
        print(f"✓ Backed up to: {backup_file}")
    
    # Get subject/grade from old metadata or defaults
    subject = old_metadata.get("subject", "Science")
    grade = old_metadata.get("grade", "10")
    
    print(f"\nRegeneration config:")
    print(f"  Subject: {subject}")
    print(f"  Grade: {grade}")
    print(f"  TTS: estimate (skip for speed)")
    print(f"  Pipeline: v2.5 (default)")
    
    # Confirm
    response = input("\nProceed with regeneration? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return None
    
    print("\n🔄 Running LLM generation...")
    
    try:
        result, tracker = process_markdown_unified(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            job_id=job_id,
            generate_tts=False,  # Skip TTS for now (can retry later)
            output_dir=job_dir,
            tts_provider="estimate",  # Just estimate durations
            dry_run=False,
            skip_wan=True,  # Skip WAN videos for now
            pipeline_version="v15_v2",  # Latest
            generation_scope="full"
        )
        
        if result:
            print(f"\n✅ Regeneration complete!")
            print(f"   Sections: {len(result.get('sections', []))}")
            
            # Run validation
            print("\n📋 Running validation...")
            os.system(f"python verify_job_content.py {job_id}")
            
            return result
        else:
            print("❌ Regeneration returned no result")
            return None
            
    except Exception as e:
        print(f"❌ Regeneration failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python regenerate_job.py <JOB_ID>")
        print("Example: python regenerate_job.py 4ee21a06")
        sys.exit(1)
    
    job_id = sys.argv[1]
    regenerate_job(job_id)
