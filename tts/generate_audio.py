import os
from pathlib import Path
from gtts import gTTS

def generate_section_audio(section: dict, output_dir: str) -> str:
    section_id = section.get("id", 1)
    narration = section.get("narration", "")
    
    if not narration:
        segments = section.get("segments", [])
        narration = " ".join([seg.get("text", "") for seg in segments])
    
    if not narration:
        narration = f"Section {section_id}: {section.get('title', 'Educational content')}"
    
    output_path = str(Path(output_dir) / f"section_{section_id}.mp3")
    
    tts = gTTS(
        text=narration,
        lang="en",
        tld="co.in",
        slow=False
    )
    
    tts.save(output_path)
    
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
