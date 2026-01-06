"""
Edge TTS POC - Test exactly how V2 Unified Pipeline uses Edge TTS

This extracts ONE segment from the presentation and tests Edge TTS with it.
"""
import asyncio
import json
from pathlib import Path

# Import exactly what the pipeline uses
try:
    import edge_tts
    from mutagen.mp3 import MP3
    print("✅ edge_tts and mutagen available")
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    exit(1)

# Load presentation
pres_path = Path("player/jobs/d76a0cc1/presentation.json")
with open(pres_path, "r", encoding="utf-8") as f:
    presentation = json.load(f)

# Get first segment from Section 2
sec2 = [s for s in presentation['sections'] if s['section_id'] == 2][0]
segments = sec2['narration']['segments']
test_segment = segments[0]

text = test_segment.get('text', '')
print(f"\n{'='*80}")
print("EDGE TTS POC - USING V2 UNIFIED PIPELINE SETTINGS")
print(f"{'='*80}")
print(f"\nTest segment text: '{text}'")
print(f"Text length: {len(text)} characters")

# Check tts_duration.py for exact voice settings
VOICE = "en-IN-NeerjaNeural"  # Indian English female voice (common default)
RATE = "+0%"  # Normal speed

print(f"\nVoice: {VOICE}")
print(f"Rate: {RATE}")

async def test_edge_tts_with_pipeline_settings():
    output_path = Path("test_edge_poc.mp3")
    
    print(f"\nGenerating audio to: {output_path}")
    
    try:
        # This is EXACTLY what the pipeline does (from _generate_edge_tts_async)
        import re
        clean_text = re.sub(r'<[^>]+/>', '', text)
        print(f"Cleaned text: '{clean_text}'")
        
        # Create communicate object
        communicate = edge_tts.Communicate(clean_text, VOICE, rate=RATE)
        
        # Save audio
        print("\nCalling Edge TTS service...")
        await communicate.save(str(output_path))
        
        if output_path.exists():
            size = output_path.stat().st_size
            print(f"\n✅ SUCCESS!")
            print(f"   File size: {size:,} bytes")
            
            if size > 1000:
                # Get duration using mutagen (same as pipeline)
                audio = MP3(output_path)
                duration = audio.info.length
                print(f"   Duration: {duration:.2f} seconds")
                print(f"\n✅ Edge TTS is working correctly!")
            else:
                print(f"\n⚠️ File is very small ({size} bytes) - might be empty")
            
            # Cleanup
            output_path.unlink()
        else:
            print("\n❌ FAILED: File was not created")
            
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
        # Try alternative voice
        print(f"\n{'='*80}")
        print("RETRY WITH ALTERNATIVE VOICE")
        print(f"{'='*80}")
        alt_voice = "en-US-AriaNeural"  # US English female
        print(f"Trying voice: {alt_voice}")
        
        try:
            communicate = edge_tts.Communicate(clean_text, alt_voice, rate=RATE)
            await communicate.save(str(output_path))
            
            if output_path.exists() and output_path.stat().st_size > 1000:
                print(f"✅ SUCCESS with alternative voice!")
                print(f"   The issue might be with voice '{VOICE}'")
                output_path.unlink()
            else:
                print(f"❌ Alternative voice also failed")
        except Exception as e2:
            print(f"❌ Alternative voice failed: {e2}")

print("\n" + "="*80)
print("STARTING EDGE TTS TEST")
print("="*80)

asyncio.run(test_edge_tts_with_pipeline_settings())

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
