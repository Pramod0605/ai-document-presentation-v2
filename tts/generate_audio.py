import os
import time
import requests
from pathlib import Path

NARAKEET_API_KEY = os.environ.get("NARAKEET_API_KEY", "")
NARAKEET_VOICE = "ravi"
NARAKEET_STREAMING_LIMIT = 1024


class TTSGenerationError(Exception):
    """Raised when TTS generation fails - NO fallback to gTTS."""
    pass


def _narakeet_streaming(narration: str, output_path: str, section_id: int) -> str:
    """Use Narakeet streaming API for short text (<= 1024 chars).
    
    Returns: output_path
    """
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
        print(f"[TTS] Section {section_id}: Narakeet streaming SUCCESS - {output_path} (actual_duration={duration}s)")
        return output_path
    else:
        raise TTSGenerationError(
            f"Narakeet streaming API failed: {response.status_code} - {response.text[:200]}"
        )


def _narakeet_polling(narration: str, output_path: str, section_id: int) -> str:
    """Use Narakeet polling API for long text (> 1024 chars).
    
    Returns: output_path
    """
    print(f"[TTS] Section {section_id}: Using Narakeet polling API (text_len={len(narration)})")
    
    response = requests.post(
        f"https://api.narakeet.com/text-to-speech/mp3?voice={NARAKEET_VOICE}",
        headers={
            "x-api-key": NARAKEET_API_KEY,
            "Content-Type": "text/plain"
        },
        data=narration.encode('utf-8'),
        timeout=30
    )
    
    if response.status_code != 200:
        raise TTSGenerationError(
            f"Narakeet polling API submission failed: {response.status_code} - {response.text[:200]}"
        )
    
    result = response.json()
    status_url = result.get('statusUrl')
    
    if not status_url:
        raise TTSGenerationError("Narakeet polling API did not return statusUrl")
    
    max_wait = 300
    poll_interval = 3
    elapsed = 0
    
    while elapsed < max_wait:
        status_response = requests.get(
            status_url,
            headers={"x-api-key": NARAKEET_API_KEY},
            timeout=30
        )
        
        if status_response.status_code != 200:
            raise TTSGenerationError(
                f"Narakeet status poll failed: {status_response.status_code}"
            )
        
        status_data = status_response.json()
        
        if status_data.get('finished'):
            if status_data.get('succeeded'):
                audio_url = status_data.get('result')
                if not audio_url:
                    raise TTSGenerationError("Narakeet finished but no result URL")
                
                audio_response = requests.get(audio_url, timeout=120)
                if audio_response.status_code != 200:
                    raise TTSGenerationError(
                        f"Failed to download audio: {audio_response.status_code}"
                    )
                
                with open(output_path, 'wb') as f:
                    f.write(audio_response.content)
                
                duration = status_data.get('durationInSeconds', 'unknown')
                print(f"[TTS] Section {section_id}: Narakeet polling SUCCESS - {output_path} (actual_duration={duration}s)")
                return output_path
            else:
                raise TTSGenerationError("Narakeet polling task failed")
        
        time.sleep(poll_interval)
        elapsed += poll_interval
    
    raise TTSGenerationError(f"Narakeet polling timed out after {max_wait}s")


def generate_section_audio(section: dict, output_dir: str) -> str:
    """Generate audio for a section using Narakeet TTS.
    
    FAIL-FAST: No fallback to gTTS. Raises TTSGenerationError if Narakeet fails.
    Uses streaming API for short text, polling API for long text.
    
    NOTE: Timing information comes from LLM's narration_segments[].duration_seconds field.
    TTS does NOT calculate or override timing - the LLM is the "brain" for timing decisions.
    
    Returns: audio file path
    """
    section_id = section.get("section_id") or section.get("id", 1)
    section_type = section.get("section_type", "content")
    narration = section.get("narration", "")
    
    # ISS-003 FIX: For recap sections, combine narration from all recap_scenes
    if section_type == "recap":
        recap_scenes = section.get("recap_scenes", [])
        if recap_scenes:
            scene_narrations = [scene.get("narration", "") for scene in recap_scenes if scene.get("narration")]
            if scene_narrations:
                narration = " ".join(scene_narrations)
                print(f"[TTS] Section {section_id}: Recap - combined {len(scene_narrations)} scene narrations (total={len(narration)} chars)")
    
    if not narration:
        segments = section.get("segments", [])
        narration = " ".join([seg.get("text", "") for seg in segments])
    
    if not narration:
        narration = f"Section {section_id}: {section.get('title', 'Educational content')}"
    
    output_path = str(Path(output_dir) / f"section_{section_id}.mp3")
    
    if not NARAKEET_API_KEY:
        raise TTSGenerationError(
            "NARAKEET_API_KEY not configured. TTS requires Narakeet API."
        )
    
    print(f"[TTS] Section {section_id}: Generating audio (voice={NARAKEET_VOICE}, text_len={len(narration)})")
    
    try:
        if len(narration) <= NARAKEET_STREAMING_LIMIT:
            return _narakeet_streaming(narration, output_path, section_id)
        else:
            return _narakeet_polling(narration, output_path, section_id)
    except requests.exceptions.RequestException as e:
        raise TTSGenerationError(f"Narakeet API request failed: {e}")


def generate_all_audio(presentation: dict, output_dir: str) -> list:
    """Generate audio for all sections in presentation.
    
    NOTE: This function only generates audio files. It does NOT modify timing data.
    Timing comes from the LLM's narration_segments[].duration_seconds field.
    The player uses LLM-provided durations directly.
    """
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
