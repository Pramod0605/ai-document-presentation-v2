
import json
import sys
import re
import random
from pathlib import Path
from core.validators.v25_validator import V25Validator

def check_fidelity(presentation, source_md_path):
    print("\n--- Phase 3: Source Fidelity Check ---")
    
    try:
        with open(source_md_path, "r", encoding="utf-8") as f:
            source_content = f.read()
    except Exception as e:
        print(f"⚠️ Could not load source markdown: {e}")
        return

    # Gather all text content from presentation
    pres_text = json.dumps(presentation)
    
    # 1. Image URL Check
    source_images = re.findall(r'!\[.*?\]\((.*?)\)', source_content)
    if source_images:
        print(f"Found {len(source_images)} images in source.")
        missing_imgs = [img for img in source_images if img not in pres_text]
        if missing_imgs:
            print(f"❌ Missing {len(missing_imgs)} images in presentation:")
            for img in missing_imgs[:3]: # Show first 3
                print(f"  - {img}")
        else:
            print("✅ All source images found in presentation.")
    else:
        print("ℹ️ No images in source markdown.")

    # 2. LaTeX Check (Simple $$...$$ detection)
    source_latex = re.findall(r'\$\$(.*?)\$\$', source_content, re.DOTALL)
    if source_latex:
        print(f"Found {len(source_latex)} LaTeX blocks in source.")
        # Clean latex for relaxed matching (remove whitespace)
        pres_text_clean = re.sub(r'\s+', '', pres_text)
        
        missing_latex = 0
        for lat in source_latex:
            lat_clean = re.sub(r'\s+', '', lat)
            if lat_clean not in pres_text_clean:
                # Try simplified check (sometimes JSON escapes slashes)
                lat_clean_esc = lat_clean.replace('\\', '\\\\')
                if lat_clean_esc not in pres_text_clean:
                    missing_latex += 1
        
        if missing_latex > 0:
            print(f"⚠️ Potential LaTeX Mismatch: {missing_latex}/{len(source_latex)} blocks might be missing or malformed.")
        else:
            print("✅ LaTeX blocks verified.")

    # 3. Content Sampling (Middle / End)
    sentences = re.split(r'[.!?]\s+', source_content)
    sentences = [s.strip() for s in sentences if len(s.split()) > 10] # Filter short noise
    
    if len(sentences) > 5:
        # Check Middle
        mid_idx = len(sentences) // 2
        mid_sample = sentences[mid_idx]
        # Check End (approx 90%)
        end_idx = int(len(sentences) * 0.9)
        end_sample = sentences[end_idx]
        
        # Simple substring check (relaxed)
        # We assume exact match might fail due to formatting, so we check distinctive phrases
        
        def check_sample(sample, label):
            # Take a distinctive chunk (first 50 chars of random sentence)
            chunk = sample[:50]
            if chunk in pres_text:
                print(f"✅ {label} Content Trace Found: '{chunk}...'")
            else:
                # Try escaping checks
                chunk_esc = json.dumps(chunk)[1:-1]
                if chunk_esc in pres_text:
                     print(f"✅ {label} Content Trace Found: '{chunk}...'")
                else:
                    print(f"❌ {label} Content Trace MISSING: '{chunk}...'")

        check_sample(mid_sample, "Middle")
        check_sample(end_sample, "End")
    else:
         print("ℹ️ Source text too short for sampling.")



def validate_job(job_id):
    job_dir = Path(f"player/jobs/{job_id}")
    pres_path = job_dir / "presentation.json"
    
    if not pres_path.exists():
        print(f"Job {job_id} not found at {pres_path}")
        return

    print(f"Validating Job {job_id} against Strict V2.5 Rules...")
    try:
        with open(pres_path, "r", encoding="utf-8") as f:
            presentation = json.load(f)
    except Exception as e:
        print(f"Failed to load JSON: {e}")
        return

    sections = presentation.get("sections", [])
    
    # 1. Global Validation (Intro, Summary, Memory, Recap, Quiz)
    print("\n--- Phase 1: Global Validation ---")
    global_data = {}
    
    # Map sections to global keys
    for sec in sections:
        stype = sec.get("type") or sec.get("section_type")
        if stype in ["intro", "summary", "memory", "recap", "quiz"]:
            global_data[stype] = sec
            
    errors = V25Validator.validate_global_response(global_data)
    if errors:
        print("❌ Global Errors:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("✅ Global structure passed.")

    # 2. Content Validation (Content, Example)
    print("\n--- Phase 2: Content Validation ---")
    content_errors_found = False
    
    for i, sec in enumerate(sections):
        stype = sec.get("type") or sec.get("section_type")
        if stype in ["content", "example"]:
            # Wrap in structure expected by validator
            chunk_data = {"sections": [sec]}
            
            # Note: We don't have source text easily available here without mapping back to markdown chunks.
            # Passing empty string means we skip pointer verification (which checks source match).
            # But we CAN check structural validity (word counts, renderers).
            
            sec_errors = V25Validator.validate_content_chunk(chunk_data, source_text="")
            
            if sec_errors:
                content_errors_found = True
                print(f"\n❌ Section {i} '{sec.get('title', 'Untitled')}' ({stype}):")
                for e in sec_errors:
                    print(f"  - {e}")
    
    if not content_errors_found:
        print("✅ All Content sections passed strict tests.")

    # 3. Fidelity Check
    source_md = job_dir / "source_markdown.md"
    check_fidelity(presentation, source_md)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_job_strict.py <job_id>")
    else:
        # Redirect stdout to a file to capture full report properly on Windows
        with open("validation_report.txt", "w", encoding="utf-8") as f:
            original_stdout = sys.stdout
            sys.stdout = f
            try:
                validate_job(sys.argv[1])
            finally:
                sys.stdout = original_stdout
        print("Validation report saved to validation_report.txt")
