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


def _narakeet_streaming(narration: str, output_path: str, section_id: int) -> tuple:
    """Use Narakeet streaming API for short text (<= 1024 chars).
    
    Returns: (output_path, duration_seconds)
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
        duration_str = response.headers.get('x-duration-seconds', '0')
        try:
            duration = float(duration_str)
        except (ValueError, TypeError):
            duration = 0.0
        print(f"[TTS] Section {section_id}: Narakeet streaming SUCCESS - {output_path} ({duration}s)")
        return output_path, duration
    else:
        raise TTSGenerationError(
            f"Narakeet streaming API failed: {response.status_code} - {response.text[:200]}"
        )


def _narakeet_polling(narration: str, output_path: str, section_id: int) -> tuple:
    """Use Narakeet polling API for long text (> 1024 chars).
    
    Returns: (output_path, duration_seconds)
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
                
                duration = status_data.get('durationInSeconds', 0.0)
                try:
                    duration = float(duration)
                except (ValueError, TypeError):
                    duration = 0.0
                print(f"[TTS] Section {section_id}: Narakeet polling SUCCESS - {output_path} ({duration}s)")
                return output_path, duration
            else:
                raise TTSGenerationError("Narakeet polling task failed")
        
        time.sleep(poll_interval)
        elapsed += poll_interval
    
    raise TTSGenerationError(f"Narakeet polling timed out after {max_wait}s")


def generate_section_audio(section: dict, output_dir: str) -> dict:
    """Generate audio for a section using Narakeet TTS.
    
    FAIL-FAST: No fallback to gTTS. Raises TTSGenerationError if Narakeet fails.
    Uses streaming API for short text, polling API for long text.
    
    Returns: dict with audio_path, duration, and timed_segments
    """
    section_id = section.get("id", 1)
    narration = section.get("narration", "")
    
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
            audio_path, duration = _narakeet_streaming(narration, output_path, section_id)
        else:
            audio_path, duration = _narakeet_polling(narration, output_path, section_id)
        
        timed_segments = _generate_timed_segments(section, duration)
        
        return {
            "audio_path": audio_path,
            "duration": duration,
            "timed_segments": timed_segments
        }
    except requests.exceptions.RequestException as e:
        raise TTSGenerationError(f"Narakeet API request failed: {e}")


def _generate_timed_segments(section: dict, actual_duration: float) -> list:
    """Generate timed_segments by scaling LLM segment durations to actual audio duration.
    
    Uses narration_segments if available, otherwise divides by segments or equally.
    """
    narration_segments = section.get("narration_segments", [])
    segments = section.get("segments", [])
    
    if narration_segments:
        source = narration_segments
        estimated_total = sum(seg.get("duration", 3.0) for seg in source)
    elif segments:
        source = segments
        estimated_total = sum(seg.get("duration", 3.0) for seg in source)
    else:
        return []
    
    if estimated_total <= 0 or actual_duration <= 0:
        return []
    
    scale_factor = actual_duration / estimated_total
    
    timed_segments = []
    current_time = 0.0
    
    for seg in source:
        text = seg.get("text", "")
        estimated_duration = seg.get("duration", 3.0)
        scaled_duration = estimated_duration * scale_factor
        
        timed_segments.append({
            "visual": text,
            "start_time": round(current_time, 2),
            "end_time": round(current_time + scaled_duration, 2)
        })
        current_time += scaled_duration
    
    if timed_segments and actual_duration > 0:
        timed_segments[-1]["end_time"] = round(actual_duration, 2)
    
    return timed_segments


def generate_all_audio(presentation: dict, output_dir: str) -> list:
    """Generate audio for all sections in presentation.
    
    Also updates each section with actual audio_duration and timed_segments.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    audio_files = []
    sections = presentation.get("sections", presentation.get("topics", []))
    
    for section in sections:
        result = generate_section_audio(section, output_dir)
        
        section["audio_duration"] = result["duration"]
        section["timed_segments"] = result["timed_segments"]
        
        audio_files.append({
            "section_id": section.get("id"),
            "section_type": section.get("section_type", "content"),
            "audio_path": result["audio_path"],
            "duration": result["duration"],
            "timed_segments_count": len(result["timed_segments"])
        })
        
        print(f"[TTS] Section {section.get('id')}: Added {len(result['timed_segments'])} timed_segments (duration={result['duration']:.1f}s)")
    
    return audio_files
