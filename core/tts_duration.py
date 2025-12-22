"""
TTS Duration v1.4 - Pass 1.5: Audio Generation & Duration Measurement

Generates TTS audio files and extracts actual duration via metadata inspection.
Updates presentation.json with real durations (not LLM estimates).

Uses Narakeet API for TTS (Indian male voice "ravi").
"""

import os
import json
import time
import logging
import tempfile
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from mutagen.mp3 import MP3

logger = logging.getLogger(__name__)

NARAKEET_API_KEY = os.environ.get("NARAKEET_API_KEY")
NARAKEET_API_URL = "https://api.narakeet.com/text-to-speech/mp3"

VOICE = "ravi"
VOICE_SPEED = 1.0

MAX_RETRIES = 3
RETRY_DELAY = 2

TEMP_AUDIO_DIR = Path("/tmp/tts_audio")


def update_durations_from_tts(
    presentation: Dict,
    output_dir: Optional[Path] = None,
    generate_audio: bool = True
) -> Dict:
    """
    Pass 1.5: Generate TTS audio and update durations in presentation.json.
    
    For each narration segment:
    1. Generate TTS audio file (Narakeet)
    2. Inspect file metadata to get exact duration
    3. Update duration_seconds field in JSON
    4. Optionally keep audio files for later use
    
    Args:
        presentation: Merged presentation.json
        output_dir: Directory to save audio files (if None, uses temp dir)
        generate_audio: If True, generate audio and measure. If False, use estimates.
        
    Returns:
        Updated presentation.json with actual durations
    """
    if not generate_audio:
        logger.info("[TTS Duration] Skipping TTS generation, using estimates")
        return presentation
    
    if not NARAKEET_API_KEY:
        logger.warning("[TTS Duration] NARAKEET_API_KEY not set, using estimates")
        return presentation
    
    if output_dir:
        audio_dir = Path(output_dir)
    else:
        audio_dir = TEMP_AUDIO_DIR
    
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("[TTS Duration] Starting TTS generation and duration measurement")
    
    total_segments = 0
    total_duration = 0.0
    
    sections = presentation.get("sections", [])
    
    for section_idx, section in enumerate(sections):
        section_id = section.get("section_id", f"section_{section_idx}")
        narration = section.get("narration", {})
        segments = narration.get("segments", [])
        
        section_duration = 0.0
        
        for seg_idx, segment in enumerate(segments):
            segment_id = segment.get("segment_id", f"seg_{seg_idx}")
            text = segment.get("text", "")
            
            if not text.strip():
                segment["duration_seconds"] = 0.0
                continue
            
            audio_path = audio_dir / f"{section_id}_{segment_id}.mp3"
            
            try:
                actual_duration = _generate_and_measure(text, audio_path)
                segment["duration_seconds"] = round(actual_duration, 2)
                section_duration += actual_duration
                total_duration += actual_duration
                total_segments += 1
                
                logger.debug(f"[TTS Duration] {segment_id}: {actual_duration:.2f}s")
                
            except Exception as e:
                logger.warning(f"[TTS Duration] Failed for {segment_id}: {e}, using estimate")
                estimate = _estimate_duration(text)
                segment["duration_seconds"] = estimate
                section_duration += estimate
                total_duration += estimate
                total_segments += 1
        
        narration["total_duration_seconds"] = round(section_duration, 2)
    
    presentation["metadata"]["total_duration_seconds"] = round(total_duration, 2)
    presentation["metadata"]["tts_segments_processed"] = total_segments
    
    logger.info(f"[TTS Duration] Processed {total_segments} segments, total duration: {total_duration:.2f}s")
    
    return presentation


def _generate_and_measure(text: str, output_path: Path) -> float:
    """
    Generate TTS audio and measure its duration.
    
    Args:
        text: Text to convert to speech
        output_path: Path to save the audio file
        
    Returns:
        Audio duration in seconds
    """
    for attempt in range(MAX_RETRIES):
        try:
            headers = {
                "x-api-key": NARAKEET_API_KEY,
                "Content-Type": "text/plain",
                "Accept": "application/octet-stream"
            }
            
            params = {
                "voice": VOICE,
                "voice-speed": VOICE_SPEED
            }
            
            response = requests.post(
                NARAKEET_API_URL,
                headers=headers,
                params=params,
                data=text.encode("utf-8"),
                timeout=60
            )
            
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                audio = MP3(output_path)
                duration = audio.info.length
                
                return duration
            
            elif response.status_code == 429:
                logger.warning(f"[TTS Duration] Rate limited, waiting...")
                time.sleep(RETRY_DELAY * (attempt + 1))
                
            else:
                logger.error(f"[TTS Duration] API error: {response.status_code}")
                raise Exception(f"Narakeet API error: {response.status_code}")
                
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"[TTS Duration] Retry {attempt + 1}/{MAX_RETRIES}: {e}")
                time.sleep(RETRY_DELAY)
            else:
                raise
    
    raise Exception(f"Failed to generate TTS after {MAX_RETRIES} attempts")


def _estimate_duration(text: str) -> float:
    """
    Estimate duration based on word count.
    Used as fallback when TTS generation fails.
    
    Average speaking rate: ~150 words per minute
    Indian English with pauses: ~130 words per minute
    """
    word_count = len(text.split())
    words_per_second = 130 / 60
    
    duration = word_count / words_per_second
    
    duration *= 1.1
    
    return round(duration, 2)


def cleanup_temp_audio(keep_files: bool = False) -> None:
    """Remove temporary audio files."""
    if keep_files:
        logger.info(f"[TTS Duration] Keeping audio files in {TEMP_AUDIO_DIR}")
        return
    
    if TEMP_AUDIO_DIR.exists():
        for file in TEMP_AUDIO_DIR.glob("*.mp3"):
            try:
                file.unlink()
            except Exception as e:
                logger.warning(f"[TTS Duration] Failed to delete {file}: {e}")
        logger.info("[TTS Duration] Cleaned up temporary audio files")


def get_total_duration(presentation: Dict) -> float:
    """Get total duration from presentation metadata or calculate it."""
    if "metadata" in presentation and "total_duration_seconds" in presentation["metadata"]:
        return presentation["metadata"]["total_duration_seconds"]
    
    total = 0.0
    for section in presentation.get("sections", []):
        for segment in section.get("narration", {}).get("segments", []):
            total += segment.get("duration_seconds", 0)
    
    return total
