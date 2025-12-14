import os
import requests
from pathlib import Path

NARAKEET_API_KEY = os.environ.get("NARAKEET_API_KEY", "")
NARAKEET_VOICE = "ravi"

def generate_section_audio(section: dict, output_dir: str) -> str:
    section_id = section.get("id", 1)
    narration = section.get("narration", "")
    
    if not narration:
        segments = section.get("segments", [])
        narration = " ".join([seg.get("text", "") for seg in segments])
    
    if not narration:
        narration = f"Section {section_id}: {section.get('title', 'Educational content')}"
    
    output_path = str(Path(output_dir) / f"section_{section_id}.mp3")
    
    if NARAKEET_API_KEY:
        try:
            response = requests.post(
                f"https://api.narakeet.com/text-to-speech/mp3?voice={NARAKEET_VOICE}",
                headers={
                    "x-api-key": NARAKEET_API_KEY,
                    "Content-Type": "text/plain",
                    "accept": "application/octet-stream"
                },
                data=narration.encode('utf-8'),
                timeout=120
            )
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                duration = response.headers.get('x-duration-seconds', 'unknown')
                print(f"Narakeet audio generated: {output_path} ({duration}s)")
                return output_path
            else:
                print(f"Narakeet API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Narakeet error: {e}")
    
    from gtts import gTTS
    tts = gTTS(
        text=narration,
        lang="en",
        tld="co.in",
        slow=False
    )
    tts.save(output_path)
    print(f"gTTS fallback audio generated: {output_path}")
    return output_path

def generate_all_audio(presentation: dict, output_dir: str) -> list:
    os.makedirs(output_dir, exist_ok=True)
    
    audio_files = []
    sections = presentation.get("sections", presentation.get("topics", []))
    
    for section in sections:
        audio_path = generate_section_audio(section, output_dir)
        audio_files.append({
            "section_id": section.get("id"),
            "section_type": section.get("section_type", "content"),
            "audio_path": audio_path
        })
    
    return audio_files
