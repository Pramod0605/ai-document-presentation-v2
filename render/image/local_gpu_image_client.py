"""
Local GPU Image Client — wan2gp-api (same server as video generation)

Generates images using local FLUX/HiDream models via the wan2gp-api
scheduler.  Images and videos share the same 3 GPU pool with round-robin
scheduling, so timeouts must match the video client (60 min).

API Endpoints (on wan2gp-api):
  POST /generate-image       → Submit image job
  GET  /status/<job_id>      → Poll status
  GET  /download-image/<job_id> → Download completed image
"""

import os
import time
import requests
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

LOCAL_GPU_URL = os.environ.get("LOCAL_GPU_URL", "http://69.197.145.4:9090")
LOCAL_GPU_API_KEY = os.environ.get("LOCAL_GPU_API_KEY", "")

# Match video client timeout: images may queue behind long video jobs
POLL_INTERVAL = 30        # seconds between status polls
MAX_POLL_ATTEMPTS = 120   # 120 × 30s = 60 min (same as video client)

# Aspect ratio → image resolution mapping
ASPECT_RATIO_TO_RESOLUTION = {
    "16:9": "1280x720",
    "9:16": "720x1280",
    "1:1":  "1024x1024",
}
DEFAULT_IMAGE_RESOLUTION = "1024x1024"


class LocalGPUImageClient:
    """Client for local GPU image generation via wan2gp-api /generate-image."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or LOCAL_GPU_URL).rstrip("/")
        self.headers = {"x-api-key": LOCAL_GPU_API_KEY} if LOCAL_GPU_API_KEY else {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Quick health check — returns True if server is reachable."""
        try:
            resp = requests.get(
                f"{self.base_url}/health", headers=self.headers, timeout=5
            )
            if resp.status_code == 200:
                logger.info("[LocalGPU-Image] Server is available")
                return True
            logger.warning(f"[LocalGPU-Image] Health check returned {resp.status_code}")
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"[LocalGPU-Image] Server unreachable: {e}")
            return False

    def generate_image(
        self,
        prompt: str,
        output_path: str,
        model: str = "flux_dev",
        resolution: str = "1024x1024",
        aspect_ratio: str = "16:9",
        steps: int = -1,
        seed: int = -1,
    ) -> Optional[str]:
        """
        Generate an image on the local GPU server.

        Flow: POST /generate-image → poll /status/<id> → GET /download-image/<id>

        Args:
            prompt:       Text prompt for image generation
            output_path:  Where to save the image file
            model:        Image model key (flux_dev, hidream_o1, flux_schnell, etc.)
            resolution:   Explicit resolution (overridden by aspect_ratio if set)
            aspect_ratio: "16:9" | "9:16" | "1:1" — maps to resolution automatically
            steps:        Denoising steps (-1 = model default)
            seed:         Random seed (-1 = random)

        Returns:
            str:  Absolute path to downloaded image on success
            None: On failure
        """
        # Idempotent: skip if valid file already exists
        if output_path:
            existing = Path(output_path)
            if existing.exists() and existing.stat().st_size > 5000:
                print(
                    f"[LocalGPU-Image] SKIP: Valid file already exists "
                    f"({existing.stat().st_size // 1024}KB): {output_path}"
                )
                return output_path

        # Map aspect_ratio → resolution (aspect_ratio takes priority)
        effective_resolution = ASPECT_RATIO_TO_RESOLUTION.get(
            aspect_ratio, resolution or DEFAULT_IMAGE_RESOLUTION
        )

        try:
            print(f"[LocalGPU-Image] Submitting job: model={model} res={effective_resolution} prompt={prompt[:80]}...")

            # Step 1: Submit job
            job_id = self._submit_job(
                prompt=prompt,
                model=model,
                resolution=effective_resolution,
                steps=steps,
                seed=seed,
            )
            if not job_id:
                return None

            print(f"[LocalGPU-Image] Job submitted: {job_id}")

            # Step 2: Poll until done
            if not self._wait_for_completion(job_id):
                return None

            # Step 3: Download image
            return self._download_image(job_id, output_path)

        except Exception as e:
            logger.error(f"[LocalGPU-Image] generate_image failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _submit_job(
        self,
        prompt: str,
        model: str = "flux_dev",
        resolution: str = "1024x1024",
        steps: int = -1,
        seed: int = -1,
    ) -> Optional[str]:
        """POST /generate-image — returns job_id or None."""
        try:
            payload = {
                "prompt": prompt,
                "model": model,
                "resolution": resolution,
                "steps": steps,
                "seed": seed,
            }

            resp = requests.post(
                f"{self.base_url}/generate-image",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            if resp.status_code != 200:
                logger.error(
                    f"[LocalGPU-Image] Submit failed: {resp.status_code} — {resp.text[:200]}"
                )
                return None

            data = resp.json()
            job_id = data.get("job_id")
            if not job_id:
                logger.error(f"[LocalGPU-Image] No job_id in response: {data}")
                return None

            queue_pos = data.get("queue_position", 0)
            gpu_id = data.get("gpu_id")
            if queue_pos > 0:
                print(
                    f"[LocalGPU-Image] Queued at position {queue_pos} "
                    f"(all GPUs busy, estimated wait: {queue_pos * 2} min)"
                )
            else:
                print(f"[LocalGPU-Image] Dispatched to GPU {gpu_id}")

            return job_id

        except requests.exceptions.RequestException as e:
            logger.error(f"[LocalGPU-Image] Submit request error: {e}")
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
                    logger.warning(
                        f"[LocalGPU-Image] Poll {attempt + 1}: status {resp.status_code}"
                    )
                    time.sleep(POLL_INTERVAL)
                    continue

                data = resp.json()
                status = data.get("status", "unknown")
                print(f"[LocalGPU-Image] Poll {attempt + 1}/{MAX_POLL_ATTEMPTS}: {status}")

                if status == "completed":
                    return True
                elif status in ("failed", "error"):
                    msg = data.get("error", "Unknown error")
                    logger.error(f"[LocalGPU-Image] Job failed: {msg}")
                    return False
                # queued / running / processing — continue polling

            except requests.exceptions.RequestException as e:
                logger.warning(f"[LocalGPU-Image] Poll request error: {e}")

            time.sleep(POLL_INTERVAL)

        logger.error(
            f"[LocalGPU-Image] Job {job_id} timed out after "
            f"{MAX_POLL_ATTEMPTS * POLL_INTERVAL}s"
        )
        return False

    def _download_image(self, job_id: str, output_path: str) -> Optional[str]:
        """GET /download-image/<job_id> — save image to output_path."""
        try:
            resp = requests.get(
                f"{self.base_url}/download-image/{job_id}",
                stream=True,
                headers=self.headers,
                timeout=60,
            )
            if resp.status_code != 200:
                logger.error(f"[LocalGPU-Image] Download failed: {resp.status_code}")
                return None

            # Detect actual extension from content-type or response headers
            content_type = resp.headers.get("content-type", "image/png")
            ext_map = {
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "image/webp": ".webp",
            }
            actual_ext = ext_map.get(content_type, ".png")

            # Ensure output path has correct extension
            out = Path(output_path).with_suffix(actual_ext)
            out.parent.mkdir(parents=True, exist_ok=True)

            with open(str(out), "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"[LocalGPU-Image] Image saved: {out} ({out.stat().st_size // 1024}KB)")
            return str(out)

        except requests.exceptions.RequestException as e:
            logger.error(f"[LocalGPU-Image] Download request error: {e}")
            return None
