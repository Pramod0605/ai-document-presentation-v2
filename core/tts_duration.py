"""
TTS Duration v1.4 - Pass 1.5: Audio Generation & Duration Measurement

Generates TTS audio files and extracts actual duration via metadata inspection.
Updates presentation.json with real durations (not LLM estimates).

Supports two TTS providers:
- narakeet: High-quality Indian voice for production
- pyttsx3: Local/offline for dry run testing (duration measurement only)
"""

import os
import json
import time
import logging
import tempfile
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Literal

MP3 = None
MutagenFile = None
pyttsx3 = None
MUTAGEN_AVAILABLE = False
PYTTSX3_AVAILABLE = False

try:
    from mutagen.mp3 import MP3
    from mutagen._file import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except ImportError:
    pass

try:
    import pyttsx3 as pyttsx3_module
    pyttsx3 = pyttsx3_module
    PYTTSX3_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)

NARAKEET_API_KEY = os.environ.get("NARAKEET_API_KEY")
NARAKEET_API_URL = "https://api.narakeet.com/text-to-speech/mp3"

VOICE = "ravi"
VOICE_SPEED = 1.0

MAX_RETRIES = 3
RETRY_DELAY = 2

TEMP_AUDIO_DIR = Path("/tmp/tts_audio")

TTSProvider = Literal["narakeet", "pyttsx3", "estimate"]


def update_durations_from_tts(
    presentation: Dict,
    output_dir: Optional[Path] = None,
    generate_audio: bool = True,
    tts_provider: TTSProvider = "narakeet"
) -> Dict:
    """
    Pass 1.5: Generate TTS audio and update durations in presentation.json.
    
    For each narration segment:
    1. Generate TTS audio file (based on provider)
    2. Inspect file metadata to get exact duration
    3. Update duration_seconds field in JSON
    4. Optionally keep audio files for later use
    
    Args:
        presentation: Merged presentation.json
        output_dir: Directory to save audio files (if None, uses temp dir)
        generate_audio: If True, generate audio and measure. If False, use estimates.
        tts_provider: "narakeet" (production), "pyttsx3" (dry run), or "estimate"
        
    Returns:
        Updated presentation.json with actual durations
    """
    if not generate_audio or tts_provider == "estimate":
        logger.info("[TTS Duration] Using word-count estimates (no audio generation)")
        return _apply_estimates(presentation)
    
    if tts_provider == "narakeet":
        if not NARAKEET_API_KEY:
            logger.warning("[TTS Duration] NARAKEET_API_KEY not set, falling back to pyttsx3")
            tts_provider = "pyttsx3"
    
    if tts_provider == "pyttsx3":
        if not PYTTSX3_AVAILABLE:
            logger.warning("[TTS Duration] pyttsx3 not available, using estimates")
            return _apply_estimates(presentation)
    
    if output_dir:
        audio_dir = Path(output_dir) / "audio"
    else:
        audio_dir = TEMP_AUDIO_DIR
    
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"[TTS Duration] Starting TTS generation with provider: {tts_provider}")
    
    pyttsx3_engine = None
    if tts_provider == "pyttsx3":
        try:
            pyttsx3_engine = pyttsx3.init()
            pyttsx3_engine.setProperty('rate', 150)
        except Exception as e:
            logger.warning(f"[TTS Duration] pyttsx3 init failed: {e}, using estimates")
            return _apply_estimates(presentation)
    
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
            
            audio_filename = f"{section_id}_{segment_id}"
            
            try:
                if tts_provider == "narakeet":
                    audio_path = audio_dir / f"{audio_filename}.mp3"
                    try:
                        actual_duration = _generate_narakeet(text, audio_path)
                    except NarakeetError as e:
                        if PYTTSX3_AVAILABLE and pyttsx3_engine is None:
                            logger.warning(f"[TTS Duration] Narakeet failed, falling back to pyttsx3: {e}")
                            pyttsx3_engine = pyttsx3.init()
                            pyttsx3_engine.setProperty('rate', 150)
                        if pyttsx3_engine:
                            audio_path = audio_dir / f"{audio_filename}.wav"
                            actual_duration = _generate_pyttsx3(text, audio_path, pyttsx3_engine)
                        else:
                            raise
                else:
                    audio_path = audio_dir / f"{audio_filename}.wav"
                    actual_duration = _generate_pyttsx3(text, audio_path, pyttsx3_engine)
                
                segment["duration_seconds"] = round(actual_duration, 2)
                segment["audio_file"] = str(audio_path.name)
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
    
    if "metadata" not in presentation:
        presentation["metadata"] = {}
    presentation["metadata"]["total_duration_seconds"] = round(total_duration, 2)
    presentation["metadata"]["tts_segments_processed"] = total_segments
    presentation["metadata"]["tts_provider"] = tts_provider
    
    logger.info(f"[TTS Duration] Processed {total_segments} segments, total duration: {total_duration:.2f}s")
    
    return presentation


class NarakeetError(Exception):
    """Raised when Narakeet API fails after all retries."""
    pass


def _generate_narakeet(text: str, output_path: Path) -> float:
    """
    Generate TTS audio using Narakeet API and measure its duration.
    
    Args:
        text: Text to convert to speech
        output_path: Path to save the audio file
        
    Returns:
        Audio duration in seconds
        
    Raises:
        NarakeetError: If Narakeet fails after all retries (allows fallback to pyttsx3)
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
                raise NarakeetError(f"Narakeet API error: {response.status_code}")
                
        except NarakeetError:
            raise
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"[TTS Duration] Retry {attempt + 1}/{MAX_RETRIES}: {e}")
                time.sleep(RETRY_DELAY)
            else:
                raise NarakeetError(f"Failed after {MAX_RETRIES} attempts: {e}")
    
    raise NarakeetError(f"Failed to generate TTS after {MAX_RETRIES} attempts")


def _generate_pyttsx3(text: str, output_path: Path, engine) -> float:
    """
    Generate TTS audio using pyttsx3 (local/offline) and measure its duration.
    
    Args:
        text: Text to convert to speech
        output_path: Path to save the audio file
        engine: pyttsx3 engine instance
        
    Returns:
        Audio duration in seconds
    """
    try:
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()
        
        if output_path.exists():
            audio = MutagenFile(output_path)
            if audio is not None and hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                return audio.info.length
            else:
                return _estimate_duration(text)
        else:
            return _estimate_duration(text)
            
    except Exception as e:
        logger.warning(f"[TTS Duration] pyttsx3 error: {e}")
        return _estimate_duration(text)


def _apply_estimates(presentation: Dict) -> Dict:
    """Apply word-count based duration estimates to all segments."""
    total_duration = 0.0
    total_segments = 0
    
    for section in presentation.get("sections", []):
        section_duration = 0.0
        for segment in section.get("narration", {}).get("segments", []):
            text = segment.get("text", "")
            estimate = _estimate_duration(text)
            segment["duration_seconds"] = estimate
            section_duration += estimate
            total_duration += estimate
            total_segments += 1
        
        if "narration" in section:
            section["narration"]["total_duration_seconds"] = round(section_duration, 2)
    
    if "metadata" not in presentation:
        presentation["metadata"] = {}
    presentation["metadata"]["total_duration_seconds"] = round(total_duration, 2)
    presentation["metadata"]["tts_segments_processed"] = total_segments
    presentation["metadata"]["tts_provider"] = "estimate"
    
    return presentation


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
        for file in TEMP_AUDIO_DIR.glob("*.*"):
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
