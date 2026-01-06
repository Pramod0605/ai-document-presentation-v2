"""
Retry TTS and Avatar Generation for Job d76a0cc1 (No LLM Required)

This script re-runs ONLY the generation steps that don't require LLM:
- TTS Audio Generation (uses Edge TTS)
- Avatar Generation (uses Avatar API)
- Skips Manim code regeneration (uses existing code files)
"""
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.tts_duration import update_durations_simplified
from core.agents.avatar_generator import AvatarGenerator

JOB_ID = "d76a0cc1"
JOBS_DIR = Path("player/jobs")
JOB_DIR = JOBS_DIR / JOB_ID

def retry_generation_no_llm():
    print(f"=" * 80)
    print(f"RETRY GENERATION FOR JOB {JOB_ID} (NO LLM REQUIRED)")
    print(f"=" * 80)
    
    # Load presentation
    pres_path = JOB_DIR / "presentation.json"
    with open(pres_path, "r", encoding="utf-8") as f:
        presentation = json.load(f)
    
    print(f"\nLoaded presentation with {len(presentation.get('sections', []))} sections")
    
    # Step 1: Check existing Manim code files
    print(f"\n{'='*80}")
    print("STEP 1: Checking Existing Manim Code Files")
    print(f"{'='*80}\n")
    
    manim_code_dir = JOB_DIR / "manim_code"
    if manim_code_dir.exists():
        code_files = list(manim_code_dir.glob("*.py"))
        print(f"✅ Found {len(code_files)} existing Manim code files")
        print("   Skipping LLM code generation - will use existing files for rendering")
    else:
        print("❌ No existing Manim code files found")
        print("   You'll need to regenerate with LLM or the videos won't render")
    
    # Step 2: Retry TTS (No LLM needed)
    print(f"\n{'='*80}")
    print("STEP 2: Regenerating TTS Audio (No LLM)")
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
        return
    
    try:
        print("\nGenerating TTS audio with Edge TTS...")
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
            if len(non_empty) < segments_with_text:
                print(f"  ⚠️  Warning: Only {len(non_empty)}/{segments_with_text} segments have audio")
        
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
    
    # Step 4: Retry Avatar Generation (No LLM needed)
    print(f"\n{'='*80}")
    print("STEP 4: Submitting Avatar Generation (No LLM)")
    print(f"{'='*80}\n")
    
    try:
        avatar_gen = AvatarGenerator()
        results = avatar_gen.submit_parallel_job(presentation, JOB_ID, str(JOB_DIR))
        print(f"✅ Avatar submission complete:")
        print(f"   - Queued: {len(results['queued'])}")
        print(f"   - Skipped: {len(results['skipped'])}")
        print(f"   - Failed: {len(results['failed'])}")
        
        if results['queued']:
            print(f"\n📝 Note: Avatar videos will be generated asynchronously.")
            print(f"   Check player/jobs/{JOB_ID}/avatar_status.json for progress")
        
    except Exception as e:
        print(f"❌ Avatar submission failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("RETRY COMPLETE (NO LLM REQUIRED)")
    print(f"{'='*80}")
    print("\n📋 Next Steps:")
    print("   1. TTS audio should now be in player/jobs/d76a0cc1/audio/")
    print("   2. Avatar generation is running in background")
    print("   3. For Manim videos, run: python -m core.renderer_executor")
    print("      (or just play the presentation - videos will render on demand)")

if __name__ == "__main__":
    retry_generation_no_llm()
