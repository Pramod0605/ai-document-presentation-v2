import asyncio
import edge_tts

async def test_edge_tts():
    """Test if Edge TTS works with a US voice"""
    test_text = "Hello, this is a test with a different voice."
    output_file = "test_audio_us.mp3"
    
    try:
        communicate = edge_tts.Communicate(test_text, "en-US-AvaNeural")
        await communicate.save(output_file)
        print(f"✅ Edge TTS working - saved to {output_file}")
    except Exception as e:
        print(f"❌ Edge TTS failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_edge_tts())
