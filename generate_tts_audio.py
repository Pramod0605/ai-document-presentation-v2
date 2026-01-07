"""
Generate TTS audio for job d76a0cc1 using pyttsx3 (local TTS)
This is a fallback when network-based TTS services are unavailable.
"""
import json
import time
from pathlib import Path
import pyttsx3
import wave
import struct
import math

JOB_ID = "d76a0cc1"
JOB_DIR = Path(f"player/jobs/{JOB_ID}")
AUDIO_DIR = JOB_DIR / "audio"
PRESENTATION_FILE = JOB_DIR / "presentation.json"

def generate_audio():
    print("=" * 60)
    print(f"GENERATING TTS AUDIO FOR JOB {JOB_ID}")
    print("Using: pyttsx3 (local/offline TTS)")
    print("=" * 60)
    
    # Initialize pyttsx3 engine
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)  # Speed
    
    # Set voice (try to get a good one)
    voices = engine.getProperty('voices')
    for voice in voices:
        if 'david' in voice.name.lower() or 'zira' in voice.name.lower():
            engine.setProperty('voice', voice.id)
            print(f"Using voice: {voice.name}")
            break
    
    # Load presentation
    with open(PRESENTATION_FILE, 'r', encoding='utf-8') as f:
        presentation = json.load(f)
    
    sections = presentation.get('sections', [])
    print(f"\nFound {len(sections)} sections")
    
    AUDIO_DIR.mkdir(exist_ok=True)
    
    success = 0
    failed = 0
    total_audio_size = 0
    
    for section in sections:
        section_id = section.get('id', 'unknown')
        narration = section.get('narration', {})
        
        # V2.5 Director format: narration.segments
        segments = narration.get('segments', [])
        
        for seg in segments:
            seg_id = seg.get('id', f"{section_id}_0")
            text = seg.get('text', '').strip()
            
            if not text:
                continue
            
            audio_file = AUDIO_DIR / f"{seg_id}.mp3"
            
            # Skip if already exists and has content
            if audio_file.exists() and audio_file.stat().st_size > 1000:
                size = audio_file.stat().st_size
                print(f"✓ {seg_id}: Already exists ({size:,} bytes)")
                total_audio_size += size
                success += 1
                continue
            
            # Clean text for TTS (limit length, remove special chars)
            clean_text = text[:400].replace('\n', ' ').replace('  ', ' ')
            
            print(f"→ {seg_id}: Generating...", end=" ", flush=True)
            
            try:
                # pyttsx3 can only save to wav, we'll keep as wav for now
                wav_file = AUDIO_DIR / f"{seg_id}.wav"
                engine.save_to_file(clean_text, str(wav_file))
                engine.runAndWait()
                
                if wav_file.exists() and wav_file.stat().st_size > 1000:
                    size = wav_file.stat().st_size
                    total_audio_size += size
                    print(f"✅ {size:,} bytes")
                    success += 1
                    # Update segment to use .wav
                    seg['audio_url'] = f"audio/{seg_id}.wav"
                else:
                    print(f"❌ Empty file")
                    failed += 1
                    
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
                failed += 1
    
    print(f"\n{'='*60}")
    print(f"COMPLETE: {success} generated, {failed} failed")
    print(f"Total audio: {total_audio_size / 1024:.1f} KB")
    print(f"{'='*60}")
    
    # Update presentation.json with audio paths
    if success > 0:
        print("\nUpdating presentation.json with audio paths...")
        with open(PRESENTATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(presentation, f, indent=2)
        print("✅ Updated presentation.json")

if __name__ == "__main__":
    generate_audio()
