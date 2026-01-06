import json
import os
import sys
import argparse
import re
from pathlib import Path

def verify(job_id):
    job_dir = Path(f"player/jobs/{job_id}")
    json_path = job_dir / "presentation.json"

    if not json_path.exists():
        print(f"❌ ERROR: {json_path} not found")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        print(f"✅ Job Loaded: {job_id}")
        print(f"Title: {data.get('title')}")
        print(f"Subject: {data.get('subject')}")
        print(f"Metadata: {json.dumps(data.get('metadata', {}), indent=2)}")
        
        sections = data.get("sections", [])
        print(f"\n🔍 Section Analysis ({len(sections)} sections):")
        
        types_found = set()
        latex_found = False
        images_found = False
        
        for i, section in enumerate(sections):
            if isinstance(section, str):
                print(f"  {i+1}. [WARNING] Skipped string section: {section[:50]}...")
                continue
                
            s_type = section.get("section_type")
            title = section.get("title")
            renderer = section.get("renderer")
            types_found.add(s_type)
            
            # --- Narration Check ---
            narration = section.get("narration", {})
            segments = []
            duration = 0
            
            if isinstance(narration, dict):
                segments = narration.get("segments", [])
                duration = narration.get("total_duration_seconds", 0)
                
                # Verify Text Exists
                full_text = narration.get("full_text", "")
                if not full_text:
                    # Try validation from segments
                    full_text = " ".join([s.get("text","") for s in segments])
                
                narr_status = "✅" if full_text.strip() else "❌ EMPTY"
            else:
                narr_status = f"⚠️ Format: {type(narration)}"

            # Audio File Check
            audio_files = [s.get("audio_file") for s in segments if isinstance(s, dict) and s.get("audio_file")]
            has_audio = len(audio_files) > 0
            
            print(f"  {i+1}. [{s_type.upper()}] '{title}'")
            print(f"     - Renderer: {renderer}")
            print(f"     - Narration: {narr_status} ({len(segments)} segs, {duration}s)")
            print(f"     - Audio Output: {'✅ Yes' if has_audio else '❌ No'}")
            
            # --- Content & Manim Checks ---
            if s_type in ["content", "example"]:
                # Check for visual content from markdown
                visuals = section.get("visual_beats", [])
                print(f"     - Visual Beats: {len(visuals)}")
                
                # LaTeX & Image Preservation Check
                # Scan visual beats for known patterns
                for beat in visuals:
                    desc = beat.get("description", "")
                    if isinstance(desc, list): desc = " ".join(desc)
                    if not isinstance(desc, str): desc = str(desc)
                    
                    # LaTeX Check ($...$ or \\( ... \\))
                    if "$" in desc or "\\(" in desc:
                        latex_found = True
                        print(f"       -> [LaTeX Detect] {desc[:50]}...")
                        
                    # Image Check
                    if "images/" in desc or beat.get("image_path"):
                        images_found = True
                        print(f"       -> [Image Detect] Found image ref")

                # Check for Manim Spec
                manim_spec = section.get("render_spec", {}).get("manim_scene_spec", {})
                if renderer == "manim":
                     if manim_spec:
                         code = manim_spec.get("manim_code", "")
                         has_code = len(code) > 10
                         print(f"     - Manim Spec: ✅ Present (Code Len: {len(code)})")
                         
                         # Check LaTeX in Manim Code
                         if "$" in code or "MathTex" in code:
                             latex_found = True
                             print(f"       -> [LaTeX Detect] Found in Manim Code")
                     else:
                         print(f"     - Manim Spec: ❌ MISSING")

            if s_type == "recap":
                # Recap usually uses video renderer in V2.5
                prompts = section.get("video_prompts", [])
                if not prompts:
                     # Check narration segments for image_prompts if video_prompts not at top
                     # Actually V2.5 Recap uses `video_prompts` list usually? 
                     # Or segments have distinct prompts.
                     pass
        
        print("\nSUMMARY COMPLIANCE CHECK:")
        required = ["intro", "summary", "content", "memory", "recap"]
        success = True
        for req in required:
            if req in types_found:
                print(f"✅ {req.capitalize()} Found")
            else:
                print(f"❌ {req.capitalize()} MISSING")
                success = False
        
        if latex_found:
            print("✅ LaTeX Patterns Preserved")
        else:
            print("⚠️ No LaTeX detected (Check input if this is expected)")
            
        if images_found:
            print("✅ Content Images Preserved")
        else:
            print("⚠️ No Content Images detected (Check input if this is expected)")

        if success:
            print("\n✅ PASSED V2.5 STRUCTURE VALIDATION")
        else:
            print("\n❌ FAILED V2.5 STRUCTURE VALIDATION")

    except Exception as e:
        print(f"❌ Validation Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Job Content")
    parser.add_argument("job_id", help="Job ID to verify")
    args = parser.parse_args()
    
    verify(args.job_id)
