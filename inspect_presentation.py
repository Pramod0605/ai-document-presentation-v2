import json
from pathlib import Path

def inspect_job(job_id):
    path = Path(f"player/jobs/{job_id}/presentation.json")
    if not path.exists():
        print(f"File not found: {path}")
        return
        
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    sections = data.get("sections", [])
    print(f"TOTAL SECTIONS: {len(sections)}")
    print(f"METADATA: {json.dumps(data.get('metadata'), indent=2)}")
    
    for i, s in enumerate(sections):
        title = s.get("title", "No Title")
        ctype = s.get("section_type", "unknown")
        renderer = s.get("renderer", "none")
        print(f"{i+1}. [{ctype}] {title} ({renderer})")
        
        # Check for LaTeX in narration or visual beats
        narr = json.dumps(s.get("narration", {}))
        beats = json.dumps(s.get("visual_beats", []))
        if "$" in narr or "$" in beats:
            print("   ✓ LaTeX detected")
        if "<table>" in narr or "<table>" in beats or "table" in str(s).lower():
            print("   ✓ Table detected")

if __name__ == "__main__":
    import sys
    inspect_job(sys.argv[1])
