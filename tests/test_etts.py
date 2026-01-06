import asyncio
import edge_tts

async def main():
    # Use a standard, confirmed voice name
    voice = "en-US-AndrewNeural" 
    text = "Hello, this is a test of the Edge TTS system."
    output_file = "hello.mp3"

    communicate = edge_tts.Communicate(text, voice)
    
    try:
        await communicate.save(output_file)
        print(f"Success! Audio saved to {output_file}")
    except edge_tts.exceptions.NoAudioReceived:
        print("Error: No audio was received. Check your internet connection or voice name.")

if __name__ == "__main__":
    # Modern way to run async code without DeprecationWarnings
    asyncio.run(main())
