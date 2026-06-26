"""
Local GPU Video Client — `38.247.187.26:8000`

Used for non-biology/anatomy video generation (general scenes, etc.)
Routing decision is made by the Director LLM at generation time via `use_local_gpu` field.

API Endpoints:
  GET  /health            → Health check
  POST /generate          → Submit job {"prompt": "...", "video_length": 125, ...}
  GET  /status/<job_id>   → Poll status {"status": "pending|processing|completed|failed"}
  GET  /download/<job_id> → Download completed video
  POST /upload            → Upload image file, returns {"token": "..."} for image_start_token / image_end_token
"""
import os
import time
import requests
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

LOCAL_GPU_URL = os.environ.get("LOCAL_GPU_URL", "http://38.247.187.26:8000")
LOCAL_GPU_API_KEY = os.environ.get("LOCAL_GPU_API_KEY", "")

POLL_INTERVAL = 30      # seconds between status polls
MAX_POLL_ATTEMPTS = 120 # 120 * 30s = 60 min (1 hour) max


class LocalGPUClient:
    """Client for local GPU video generation server."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or LOCAL_GPU_URL).rstrip("/")
        self.headers = {"x-api-key": LOCAL_GPU_API_KEY} if LOCAL_GPU_API_KEY else {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Quick health check — returns True if server is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/health", headers=self.headers, timeout=5)
            if resp.status_code == 200:
                logger.info("[LocalGPU] Server is available")
                return True
            logger.warning(f"[LocalGPU] Health check returned {resp.status_code}")
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"[LocalGPU] Server unreachable: {e}")
            return False

    def upload_file(self, file_path: str) -> Optional[str]:
        """
        Upload an image file to obtain a server-side token for image-to-video generation.

        POST /upload — multipart/form-data  {"file": <binary>}
        Returns: token string (used as image_start_token / image_end_token) or None on failure.
        """
        try:
            with open(file_path, "rb") as f:
                files = {"file": (Path(file_path).name, f)}
                resp = requests.post(
                    f"{self.base_url}/upload",
                    files=files,
                    headers=self.headers,
                    timeout=60,
                )
            if resp.status_code != 200:
                logger.error(
                    f"[LocalGPU] Upload failed: {resp.status_code} — {resp.text[:200]}"
                )
                return None

            data = resp.json()
            # Server may use any of these keys
            token = (
                data.get("token")
                or data.get("image_token")
                or data.get("file_token")
            )
            if token:
                logger.info(f"[LocalGPU] Uploaded {Path(file_path).name} → token: {str(token)[:20]}...")
                return token

            logger.error(f"[LocalGPU] No token in upload response: {data}")
            return None

        except Exception as e:
            logger.error(f"[LocalGPU] upload_file error: {e}")
            return None

    def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        output_path: Optional[str] = None,
        image_path: Optional[str] = None,
        image_path_end: Optional[str] = None,
        aspect_ratio: str = "16:9",
    ) -> Optional[str]:
        """
        Generate a video on the local GPU server.

        Args:
            prompt: Text prompt describing the video content
            duration: Duration in seconds (clamped 5–15)
            output_path: Where to save the downloaded .mp4
            image_path: Optional start-frame image path for image-to-video (I2V)
            image_path_end: Optional end-frame image path for smooth start→end transition
            aspect_ratio: "16:9" (1280×720, default) or "9:16" (720×1280)

        Returns:
            str: Path to downloaded .mp4 file on success
            None: On failure (caller should fallback to Kie.ai WAN)
        """
        # V2.6 IDEMPOTENT: Skip if valid file already exists (mirrors wan_runner.py behaviour)
        if output_path:
            existing = Path(output_path)
            if existing.exists() and existing.stat().st_size > 10000:
                print(f"[LocalGPU] SKIP: Valid file already exists ({existing.stat().st_size // 1024}KB): {output_path}")
                return output_path

        # ── I2V: Upload start frame ──────────────────────────────────────────
        image_token = None
        if image_path and Path(image_path).exists():
            print(f"[LocalGPU] Uploading start-frame: {image_path}")
            image_token = self.upload_file(image_path)
            if not image_token:
                logger.error("[LocalGPU] Start-frame upload failed — aborting I2V job")
                return None

        # ── I2V: Upload end frame (non-fatal) ────────────────────────────────
        image_end_token = None
        if image_path_end and Path(image_path_end).exists():
            print(f"[LocalGPU] Uploading end-frame: {image_path_end}")
            image_end_token = self.upload_file(image_path_end)
            if not image_end_token:
                logger.warning("[LocalGPU] End-frame upload failed — continuing with start frame only")

        try:
            mode = "I2V" if image_token else "T2V"
            print(f"[LocalGPU] Submitting {mode} job: {prompt[:80]}...")

            # Step 1: Submit job
            job_id = self._submit_job(prompt, duration, image_token, image_end_token, aspect_ratio)
            if not job_id:
                return None

            print(f"[LocalGPU] Job submitted: {job_id}")

            # Step 2: Poll until done
            if not self._wait_for_completion(job_id):
                return None

            # Step 3: Download video
            return self._download_video(job_id, output_path)

        except Exception as e:
            logger.error(f"[LocalGPU] generate_video failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _submit_job(
        self,
        prompt: str,
        duration: int,
        image_token: Optional[str] = None,
        image_end_token: Optional[str] = None,
        aspect_ratio: str = "16:9",
    ) -> Optional[str]:
        """POST /generate — returns job_id or None."""
        try:
            # Clamp duration to [5, 15] seconds and convert to frames (25 fps)
            _clamped = max(5, min(15, int(round(duration))))
            video_length = _clamped * 25
            if _clamped != int(round(duration)):
                logger.warning(
                    f"[LocalGPU] Duration clamped: {duration}s → {_clamped}s ({video_length} frames)"
                )

            payload: dict = {
                "prompt": prompt,
                "video_length": video_length,
                "resolution": {
                    "16:9": "1280x720",
                    "9:16": "720x1280",
                }.get(aspect_ratio, "1280x720"),
                "model": "ltx23_distilled_q6",
                "seed": 42,
            }

            if image_token:
                payload["image_start_token"] = image_token

            if image_end_token:
                payload["image_end_token"] = image_end_token

            resp = requests.post(
                f"{self.base_url}/generate",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            if resp.status_code != 200:
                logger.error(f"[LocalGPU] Submit failed: {resp.status_code} — {resp.text[:200]}")
                return None

            data = resp.json()
            job_id = data.get("job_id")
            if not job_id:
                logger.error(f"[LocalGPU] No job_id in response: {data}")
                return None
            return job_id

        except requests.exceptions.RequestException as e:
            logger.error(f"[LocalGPU] Submit request error: {e}")
            return None

    def _wait_for_completion(self, job_id: str) -> bool:
        """Poll GET /status/<job_id> until completed or failed."""
        for attempt in range(MAX_POLL_ATTEMPTS):
            try:
                resp = requests.get(
                    f"{self.base_url}/status/{job_id}",
                    headers=self.headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    logger.warning(f"[LocalGPU] Poll {attempt+1}: status {resp.status_code}")
                    time.sleep(POLL_INTERVAL)
                    continue

                data = resp.json()
                status = data.get("status", "unknown")
                print(f"[LocalGPU] Poll {attempt+1}/{MAX_POLL_ATTEMPTS}: {status}")

                if status == "completed":
                    return True
                elif status == "failed":
                    msg = data.get("error", "Unknown error")
                    logger.error(f"[LocalGPU] Job failed: {msg}")
                    return False
                # pending / processing — continue polling

            except requests.exceptions.RequestException as e:
                logger.warning(f"[LocalGPU] Poll request error: {e}")

            time.sleep(POLL_INTERVAL)

        logger.error(f"[LocalGPU] Job {job_id} timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL}s")
        return False

    def _download_video(self, job_id: str, output_path: Optional[str]) -> Optional[str]:
        """GET /download/<job_id> — save video to output_path."""
        try:
            resp = requests.get(
                f"{self.base_url}/download/{job_id}",
                stream=True,
                headers=self.headers,
                timeout=120,
            )
            if resp.status_code != 200:
                logger.error(f"[LocalGPU] Download failed: {resp.status_code}")
                return None

            out = output_path or f"local_gpu_{job_id}_{int(time.time())}.mp4"
            Path(out).parent.mkdir(parents=True, exist_ok=True)

            with open(out, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"[LocalGPU] Video saved: {out}")
            return out

        except requests.exceptions.RequestException as e:
            logger.error(f"[LocalGPU] Download request error: {e}")
            return None
