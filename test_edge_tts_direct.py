"""
Test Edge TTS directly to see if it's a service issue
"""
import asyncio
from pathlib import Path

# Test if edge_tts is available
try:
    import edge_tts
    print("edge_tts module: AVAILABLE")
except ImportError as e:
    print(f"edge_tts module: NOT AVAILABLE - {e}")
    exit(1)

async def test_edge_tts():
    test_text = "Hello, this is a test of the Edge TTS service."
    output_path = Path("test_edge_output.mp3")
    
    print(f"\nTesting Edge TTS with text: '{test_text}'")
    print(f"Output: {output_path}")
    
    try:
        communicate = edge_tts.Communicate(test_text, "en-US-AriaNeural")
        await communicate.save(str(output_path))
        
        if output_path.exists():
            size = output_path.stat().st_size
            print(f"\nSUCCESS! Generated {size} bytes")
            if size > 1000:
                print("File size looks good (> 1KB)")
            else:
                print("WARNING: File is very small, might be empty")
            
            # Clean up
            output_path.unlink()
        else:
            print("\nFAILED: File was not created")
            
    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_edge_tts())
