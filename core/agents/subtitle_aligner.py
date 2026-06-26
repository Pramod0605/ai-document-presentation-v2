"""
subtitle_aligner.py
===================
Generate word-level subtitle timings from avatar videos using faster-whisper.

Per-section workflow:
  avatar/section_N_avatar.mp4
    → extract audio (ffmpeg) → temp wav
    → faster-whisper transcribe → word timestamps
    → write subtitles/section_N_subtitles.json

Output format (subtitles/section_N_subtitles.json):
{
  "section_id": 3,
  "words": [
    {"word": "Hello", "start": 0.0, "end": 0.38},
    {"word": "world", "start": 0.40, "end": 0.72},
    ...
  ]
}

The player loads each section's subtitle file independently — no global subtitles.json.
"""

import os
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-load model to avoid import cost at startup
_model = None
_MODEL_SIZE = "base"  # fast + accurate enough for narration content


def _get_model():
    """Lazy-load the faster-whisper model (cached after first load)."""
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
            # Use int8 quantization on CPU for speed, or float16 on GPU
            device = "cuda" if _cuda_available() else "cpu"
            compute = "float16" if device == "cuda" else "int8"
            logger.info(f"[Subtitle] Loading faster-whisper '{_MODEL_SIZE}' on {device} ({compute})")
            _model = WhisperModel(_MODEL_SIZE, device=device, compute_type=compute)
            logger.info("[Subtitle] Model loaded ✅")
        except Exception as e:
            logger.error(f"[Subtitle] Failed to load faster-whisper model: {e}")
            raise
    return _model


def _cuda_available() -> bool:
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def _extract_audio(video_path: str, wav_path: str) -> bool:
    """Extract mono 16kHz WAV from video — whisper's preferred format."""
    try:
        r = subprocess.run(
            [
                "ffmpeg", "-y", "-i", video_path,
                "-vn",                  # no video
                "-ar", "16000",         # 16kHz sample rate
                "-ac", "1",             # mono
                "-f", "wav", wav_path,
            ],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            logger.warning(f"[Subtitle] ffmpeg audio extract failed: {r.stderr[-300:]}")
            return False
        return True
    except Exception as e:
        logger.warning(f"[Subtitle] Audio extract exception: {e}")
        return False


def generate_subtitles_for_section(
    section_id: int,
    avatar_video_path: str,
    output_dir: str,
    language: Optional[str] = None,
) -> Optional[str]:
    """
    Generate subtitles for a single section's avatar video.

    Args:
        section_id:       Section number (used to name output file).
        avatar_video_path: Absolute path to the avatar .mp4 file.
        output_dir:       Job root dir (subtitles/ subdir will be created).
        language:         Optional language hint for whisper (e.g. "hi" for Hindi).

    Returns:
        Path to the written subtitles JSON, or None on failure.
    """
    avatar_path = Path(avatar_video_path)
    if not avatar_path.exists():
        logger.warning(f"[Subtitle] Avatar not found: {avatar_video_path}")
        return None

    subtitles_dir = Path(output_dir) / "subtitles"
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    out_json = subtitles_dir / f"section_{section_id}_subtitles.json"

    # Use a temp dir for the WAV so we never leave stray audio files
    with tempfile.TemporaryDirectory() as tmp_dir:
        wav_path = os.path.join(tmp_dir, f"sec{section_id}_audio.wav")

        # 1. Extract audio
        if not _extract_audio(str(avatar_path), wav_path):
            return None

        # 2. Transcribe
        try:
            model = _get_model()
            transcribe_kwargs = {"word_timestamps": True}
            if language:
                # Map V2 language names → ISO codes whisper understands
                lang_map = {
                    "hindi": "hi", "tamil": "ta", "telugu": "te",
                    "kannada": "kn", "malayalam": "ml", "bengali": "bn",
                    "marathi": "mr", "gujarati": "gu", "punjabi": "pa",
                    "english": "en",
                }
                iso = lang_map.get(language.lower(), language[:2].lower())
                transcribe_kwargs["language"] = iso

            segments, info = model.transcribe(wav_path, **transcribe_kwargs)

            words = []
            for seg in segments:
                if seg.words:
                    for w in seg.words:
                        words.append({
                            "word": w.word.strip(),
                            "start": round(w.start, 3),
                            "end": round(w.end, 3),
                        })

            logger.info(
                f"[Subtitle] Sec {section_id}: {len(words)} words transcribed "
                f"(lang detected: {info.language})"
            )

        except Exception as e:
            logger.error(f"[Subtitle] Transcription failed for sec {section_id}: {e}")
            return None

    # 3. Write JSON
    payload = {
        "section_id": section_id,
        "words": words,
    }
    try:
        out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        logger.info(f"[Subtitle] ✅ Written: {out_json.name} ({len(words)} words)")
        return str(out_json)
    except Exception as e:
        logger.error(f"[Subtitle] Failed to write {out_json}: {e}")
        return None
