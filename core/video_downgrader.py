"""
video_downgrader.py
===================
Compress Local GPU (LTX/WAN) beat videos in jobs/<id>/videos/ using CRF 26.

LTX/WAN outputs are always high-bitrate raw video (18-35 Mbps) regardless of
resolution. CRF 26 re-encoding reduces 35MB → ~3-5MB with negligible visual loss.

V2 has NO merged final videos — every file in videos/ is a raw LTX/WAN beat.
Avatar videos live in avatars/ and are NEVER touched.

Real V2 filename patterns (verified from actual job dirs):
  videos/topic_3_beat_1.mp4          ← legacy/fallback
  videos/topic_11_seg_2_beat_1.mp4   ← new (section partitioner)
"""

import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Exact V2 beat filename patterns (verified from real job dirs)
_BEAT_PATTERNS = [
    "topic_*_beat_*.mp4",        # legacy: topic_3_beat_1.mp4 / topic_3_beat_0.mp4
    "topic_*_seg_*_beat_*.mp4",  # new:    topic_11_seg_2_beat_1.mp4
]


def _ffprobe_wh(path: str):
    """Return (width, height) tuple or None if probe fails."""
    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=s=x:p=0",
                path,
            ],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and "x" in r.stdout.strip():
            w, h = r.stdout.strip().split("x")
            return int(w), int(h)
    except Exception:
        pass
    return None


def _compress_file(path: str, target_w: int, target_h: int, crf: int, preset: str = "medium") -> str:
    """
    Re-encode a single LTX/WAN beat file with CRF to reduce bitrate.
    Always re-encodes — LTX outputs are always high-bitrate raw video.
    Returns: 'ok' | 'error'
    Original is only overwritten if FFmpeg succeeds — non-destructive on failure.
    """
    p = Path(path)
    if not p.exists():
        return "error"

    tmp = str(p.parent / f".tmp_dg_{p.name}")
    try:
        cmd = [
            "ffmpeg", "-y", "-i", path,
            "-vf",
            (
                f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black"
            ),
            "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
            "-c:a", "copy",
            tmp,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if r.returncode != 0 or not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
            logger.warning(f"[Downscaler] FFmpeg failed for {p.name}: {r.stderr[-400:]}")
            if os.path.exists(tmp):
                os.remove(tmp)
            return "error"

        original_mb = round(p.stat().st_size / 1024 / 1024, 1)
        os.replace(tmp, path)  # atomic rename — original only replaced on success
        new_mb = round(Path(path).stat().st_size / 1024 / 1024, 1)
        logger.info(f"[Downscaler] ✅ {p.name}: {original_mb}MB → {new_mb}MB")
        return "ok"

    except subprocess.TimeoutExpired:
        logger.warning(f"[Downscaler] FFmpeg timed out for {p.name}")
        if os.path.exists(tmp):
            os.remove(tmp)
        return "error"
    except Exception as e:
        logger.warning(f"[Downscaler] Exception for {p.name}: {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        return "error"


def downgrade_job_videos(job_dir: str) -> dict:
    """
    CRF-compress all LTX/WAN beat videos in jobs/<id>/videos/.

    LTX outputs are always high-bitrate raw video (18-35 Mbps).
    CRF 26 re-encoding reduces to ~2-5 Mbps with negligible visual loss.

    Scope:
      - ONLY processes videos/ directory
      - avatars/ is NEVER touched (HeyGem face recordings)
      - No merged finals exist in V2

    Returns:
      dict with keys: compressed, errors (list of filenames)
    """
    result: dict = {"compressed": 0, "errors": []}
    videos_dir = Path(job_dir) / "videos"

    if not videos_dir.exists():
        logger.info(f"[Downscaler] No videos/ dir in {job_dir} — nothing to compress")
        return result

    # Collect all beat files matching V2 patterns (deduplicated)
    beat_files: list[Path] = []
    for pat in _BEAT_PATTERNS:
        beat_files.extend(videos_dir.glob(pat))
    beat_files = sorted(set(beat_files))

    if not beat_files:
        logger.info(f"[Downscaler] No beat videos found in {videos_dir}")
        return result

    logger.info(f"[Downscaler] Compressing {len(beat_files)} LTX beat videos → CRF 26 (1280×720 max)")

    for f in beat_files:
        status = _compress_file(str(f), target_w=1280, target_h=720, crf=26, preset="medium")
        if status == "ok":
            result["compressed"] += 1
        else:
            result["errors"].append(f.name)
            logger.warning(f"[Downscaler] ❌ {f.name}: failed (original kept)")

    logger.info(
        f"[Downscaler] Done — compressed={result['compressed']}, errors={len(result['errors'])}"
    )
    return result
