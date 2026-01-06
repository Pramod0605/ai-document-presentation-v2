import json
import statistics
from pathlib import Path

JOB_ID = "6d54aa37"
JOBS_DIR = Path("player/jobs")

def analyze_job(job_id):
    job_dir = JOBS_DIR / job_id
    pres_path = job_dir / "presentation.json"
    source_path = job_dir / "source_markdown.md"
    
    if not pres_path.exists():
        print(f"❌ Presentation not found for {job_id}")
        return

    # Load Source Statistics
    source_stats = {"chars": 0, "lines": 0}
    if source_path.exists():
        content = source_path.read_text(encoding="utf-8")
        source_stats["chars"] = len(content)
        source_stats["lines"] = len(content.splitlines())
        
    # Load Presentation
    with open(pres_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    sections = data.get("sections", [])
    
    # Analysis Counters
    total_words = 0
    total_tables = 0
    total_images = 0
    total_diagrams = 0
    total_code_blocks = 0
    
    print(f"=== Content Analysis for Job {job_id} ===")
    print(f"Source size: {source_stats['chars']} chars, {source_stats['lines']} lines")
    print(f"Generated Sections: {len(sections)}")
    
    for i, section in enumerate(sections):
        s_title = section.get("title", "Untitled")
        s_type = section.get("type", "unknown")
        
        # Count Content
        # Unified Pipeline uses 'narration.full_text'
        narration_obj = section.get("narration", {})
        narration_text = narration_obj.get("full_text", "")
        
        # Check visual beats
        beats = section.get("visual_beats", [])
        beats_text = ""
        
        for beat in beats:
            beats_text += beat.get("description", "") + " "
            beats_text += beat.get("text_overlay", "") + " " # If it exists
            
            # Count Media in beats
            v_type = beat.get("visual_type")
            if v_type == "table":
                total_tables += 1
            elif v_type == "image":
                total_images += 1
            elif v_type == "code":
                total_code_blocks += 1
            elif v_type == "diagram":
                total_diagrams += 1
                
        words = len(narration_text.split()) + len(beats_text.split())
        total_words += words
        
        print(f"  Sec {i+1} [{s_type}]: {s_title[:40]}... ({words} words)")
        
        # DEBUG: Print structure of first section if empty
        if i == 0 and words == 0:
            print("\nDEBUG: First Section Structure:")
            print(json.dumps(section, indent=2)[:500])
            print("\n")

    print("-" * 30)
    print(f"Total Words (Presentation): {total_words}")
    print(f"Total Tables Detected: {total_tables}")
    print(f"Total Images Detected: {total_images}")
    print(f"Total Diagrams Detected: {total_diagrams}")
    print(f"Total Code Blocks: {total_code_blocks}")
    print("=" * 30)

if __name__ == "__main__":
    analyze_job(JOB_ID)
