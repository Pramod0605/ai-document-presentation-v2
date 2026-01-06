"""
Retry TTS with pyttsx3 Fallback (Offline TTS - No Network Required)

This script uses pyttsx3 (Windows SAPI5) instead of Edge TTS.
It works completely offline and doesn't require internet.
"""
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.tts_duration import update_durations_simplified

JOB_ID = "d76a0cc1"
JOBS_DIR = Path("player/jobs")
JOB_DIR = JOBS_DIR / JOB_ID

def retry_tts_offline():
    print(f"=" * 80)
    print(f"RETRY TTS FOR JOB {JOB_ID} (OFFLINE MODE - pyttsx3)")
    print(f"=" * 80)
    print("\nNOTE: Using pyttsx3 (Windows SAPI5) because Edge TTS service is unavailable.")
    print("Audio quality will be different but generation is guaranteed to work offline.\n")
    
    # Load presentation
    pres_path = JOB_DIR / "presentation.json"
    with open(pres_path, "r", encoding="utf-8") as f:
        presentation = json.load(f)
    
    print(f"Loaded presentation with {len(presentation.get('sections', []))} sections")
    
    # Check segments
    total_segments = 0
    segments_with_text = 0
    for section in presentation.get("sections", []):
        segs = section.get("narration", {}).get("segments", [])
        total_segments += len(segs)
        segments_with_text += sum(1 for s in segs if s.get("text", "").strip())
    
    print(f"\nPre-TTS check:")
    print(f"  Total segments: {total_segments}")
    print(f"  Segments with text: {segments_with_text}")
    
    if segments_with_text == 0:
        print("\n ERROR: No segments have text!")
        return
    
    try:
        print(f"\nGenerating TTS audio with pyttsx3 (offline)...")
        print("This will take a few minutes for 71 segments...")
        
        presentation = update_durations_simplified(
            presentation,
            output_dir=JOB_DIR,
            production_provider="pyttsx3"  # Use offline TTS
        )
        print("\nSUCCESS: TTS generation complete!")
        
        # Verify audio
        audio_dir = JOB_DIR / "audio"
        if audio_dir.exists():
            audio_files = list(audio_dir.glob("*.wav"))  # pyttsx3 generates WAV
            audio_files += list(audio_dir.glob("*.mp3"))
            non_empty = [f for f in audio_files if f.stat().st_size > 1000]
            print(f"  Generated {len(non_empty)} non-empty audio files")
            
            if len(non_empty) < segments_with_text:
                print(f"  WARNING: Only {len(non_empty)}/{segments_with_text} segments have audio")
        
        # Save
        with open(pres_path, "w", encoding="utf-8") as f:
            json.dump(presentation, f, indent=4)
        print(f"\nSaved updated presentation to {pres_path}")
        
        print(f"\n{'='*80}")
        print("TTS GENERATION COMPLETE (OFFLINE MODE)")
        print(f"{'='*80}")
        print("\nNext steps:")
        print("  1. Audio files are in player/jobs/d76a0cc1/audio/")
        print("  2. You can now play the presentation")
        print("  3. Or run retry_job_no_llm.py to also submit avatar generation")
        
    except Exception as e:
        print(f"\nERROR: TTS generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    retry_tts_offline()
