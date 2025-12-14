import os
from pathlib import Path
from gtts import gTTS

def generate_topic_audio(topic: dict, output_dir: str) -> str:
    topic_id = topic.get("id", 1)
    narration = topic.get("narration", "")
    
    if not narration:
        segments = topic.get("segments", [])
        narration = " ".join([seg.get("text", "") for seg in segments])
    
    if not narration:
        narration = f"Topic {topic_id}: {topic.get('title', 'Educational content')}"
    
    output_path = str(Path(output_dir) / f"topic_{topic_id}.mp3")
    
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
    topics = presentation.get("topics", [])
    
    for topic in topics:
        audio_path = generate_topic_audio(topic, output_dir)
        audio_files.append({
            "topic_id": topic.get("id"),
            "audio_path": audio_path
        })
    
    return audio_files
