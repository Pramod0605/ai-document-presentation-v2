import asyncio
import edge_tts

async def test_edge_tts():
    """Test if Edge TTS works with a simple string"""
    test_text = "Hello, this is a test."
    output_file = "test_audio.mp3"
    
    try:
        communicate = edge_tts.Communicate(test_text, "en-IN-NeerjaNeural")
        await communicate.save(output_file)
        print(f"✅ Edge TTS working - saved to {output_file}")
    except Exception as e:
        print(f"❌ Edge TTS failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_edge_tts())
