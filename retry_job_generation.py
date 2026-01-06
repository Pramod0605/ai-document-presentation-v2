"""
Retry TTS, Avatar Generation, and Manim Code Generation for Job d76a0cc1

This script re-runs the generation steps that were affected by the V2.5 Director data format issue.
"""
import json
import sys
from pathlib import Path

# Load environment variables FIRST (before importing core modules that need API keys)
from dotenv import load_dotenv
load_dotenv()  # This loads .env file into environment

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.tts_duration import update_durations_simplified
from core.agents.avatar_generator import AvatarGenerator
from core.agents.manim_code_generator import ManimCodeGenerator, integrate_manim_code_into_section

JOB_ID = "d76a0cc1"
JOBS_DIR = Path("player/jobs")
JOB_DIR = JOBS_DIR / JOB_ID

def retry_generation():
    print(f"=" * 80)
    print(f"RETRY GENERATION FOR JOB {JOB_ID}")
    print(f"=" * 80)
    
    # Load presentation
    pres_path = JOB_DIR / "presentation.json"
    with open(pres_path, "r", encoding="utf-8") as f:
        presentation = json.load(f)
    
    print(f"\nLoaded presentation with {len(presentation.get('sections', []))} sections")
    
    # Step 1: Retry Manim Code Generation
    print(f"\n{'='*80}")
    print("STEP 1: Regenerating Manim Code")
    print(f"{'='*80}\n")
    
    manim_gen = ManimCodeGenerator()
    sections = presentation.get("sections", [])
    manim_count = 0
    
    for idx, section in enumerate(sections):
        if section.get("renderer") == "manim":
            print(f"[{idx+1}/{len(sections)}] Processing Section {section.get('section_id')}: {section.get('title')}")
            
            # Transform V2.5 Director data to Manim format (same fix as pipeline)
            nar = section.get("narration", {})
            segments = nar.get("segments", [])
            
            render_spec = section.get("render_spec", {})
            manim_spec_from_director = render_spec.get("manim_scene_spec")
            if isinstance(manim_spec_from_director, dict):
                manim_spec_from_director = manim_spec_from_director.get("description", "")
            
            section_data = {
                "section_title": section.get("title", "Section"),
                "narration_segments": segments,
                "manim_spec": manim_spec_from_director or section.get("explanation_plan", ""),
                "visual_description": "",
                "formulas": [],
                "key_terms": []
            }
            
            print(f"   → Found {len(segments)} narration segments")
            
            try:
                code = manim_gen.generate_code(section_data, style_config={"style": "standard"})
                integrate_manim_code_into_section(section, code)
                
                # Save to file
                manim_code_dir = JOB_DIR / "manim_code"
                manim_code_dir.mkdir(exist_ok=True)
                code_file = manim_code_dir / f"section_{section.get('section_id')}.py"
                with open(code_file, "w", encoding="utf-8") as f:
                    f.write(code)
                
                print(f"   ✅ Generated {len(code)} chars of code → {code_file.name}")
                manim_count += 1
            except Exception as e:
                print(f"   ❌ Failed: {e}")
    
    print(f"\n✅ Manim code generation complete: {manim_count} sections")
    
    # Step 2: Retry TTS
    print(f"\n{'='*80}")
    print("STEP 2: Regenerating TTS Audio")
    print(f"{'='*80}\n")
    
    # Debug: Check what TTS will see
    total_segments = 0
    segments_with_text = 0
    for section in presentation.get("sections", []):
        segs = section.get("narration", {}).get("segments", [])
        total_segments += len(segs)
        segments_with_text += sum(1 for s in segs if s.get("text", "").strip())
    
    print(f"Pre-TTS check:")
    print(f"  Total segments across all sections: {total_segments}")
    print(f"  Segments with non-empty text: {segments_with_text}")
    print(f"  Ready for TTS: {segments_with_text > 0}")
    
    if segments_with_text == 0:
        print("⚠️  WARNING: No segments have text! TTS will not generate any audio.")
        print("   This indicates the V2.5 Director data format issue is still present.")
        return
    
    try:
        presentation = update_durations_simplified(
            presentation,
            output_dir=JOB_DIR,
            production_provider="edge_tts"
        )
        print("✅ TTS generation complete")
        
        # Verify audio was generated
        audio_dir = JOB_DIR / "audio"
        if audio_dir.exists():
            audio_files = list(audio_dir.glob("*.mp3"))
            non_empty = [f for f in audio_files if f.stat().st_size > 1000]
            print(f"  Generated {len(non_empty)} non-empty audio files (out of {len(audio_files)} total)")
        
    except Exception as e:
        print(f"❌ TTS generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 3: Save updated presentation
    print(f"\n{'='*80}")
    print("STEP 3: Saving Updated Presentation")
    print(f"{'='*80}\n")
    
    with open(pres_path, "w", encoding="utf-8") as f:
        json.dump(presentation, f, indent=4)
    print(f"✅ Saved to {pres_path}")
    
    # Step 4: Retry Avatar Generation
    print(f"\n{'='*80}")
    print("STEP 4: Submitting Avatar Generation")
    print(f"{'='*80}\n")
    
    try:
        avatar_gen = AvatarGenerator()
        results = avatar_gen.submit_parallel_job(presentation, JOB_ID, str(JOB_DIR))
        print(f"✅ Avatar submission complete:")
        print(f"   - Queued: {len(results['queued'])}")
        print(f"   - Skipped: {len(results['skipped'])}")
        print(f"   - Failed: {len(results['failed'])}")
    except Exception as e:
        print(f"❌ Avatar submission failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("RETRY COMPLETE")
    print(f"{'='*80}")

if __name__ == "__main__":
    retry_generation()
