"""
Test our custom TTS API integration
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from core.tts_duration import _generate_our_tts, OUR_TTS_BASE_URL

def test_our_tts():
    print("=" * 60)
    print("TESTING OUR CUSTOM TTS API")
    print("=" * 60)
    print(f"\nAPI URL: {OUR_TTS_BASE_URL}")
    
    test_text = "Hello, this is a test of our custom TTS API. Namaste students!"
    output_path = Path("test_our_tts_output.wav")
    
    print(f"Test text: '{test_text}'")
    print(f"Output: {output_path}\n")
    
    try:
        print("Calling API...")
        duration = _generate_our_tts(test_text, output_path)
        
        if output_path.exists():
            size = output_path.stat().st_size
            print(f"\n✅ SUCCESS!")
            print(f"   File size: {size:,} bytes")
            print(f"   Duration: {duration:.2f} seconds")
            
            # Cleanup
            output_path.unlink()
            print(f"   Cleaned up test file")
        else:
            print("\n❌ FAILED: File not created")
            
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_our_tts()
