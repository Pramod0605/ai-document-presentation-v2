"""
Image Generator Client - Generates images from text prompts using Gemini/OpenRouter API
Used for: image_to_video reference frames, infographic static images
"""

import os
import base64
import requests
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_IMAGE_MODEL = os.environ.get(
    "OPENROUTER_IMAGE_MODEL", "google/gemini-3.1-flash-image-preview"
)

IMAGE_OUTPUT_DIR = "jobs"


class ImageGeneratorError(Exception):
    pass


def _detect_extension(image_bytes: bytes) -> str:
    """Detect image format from magic bytes and return the correct file extension."""
    if image_bytes[:3] == b'\xff\xd8\xff':
        return '.jpg'
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return '.png'
    if len(image_bytes) >= 12 and image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        return '.webp'
    return '.jpg'  # safe default — JPEG is most common from Gemini


def _save_image(image_bytes: bytes, output_path: str) -> str:
    """
    Save image bytes to disk, using the correct extension detected from magic bytes.
    Returns the actual file path (may differ from output_path if extension changed).
    """
    ext = _detect_extension(image_bytes)
    p = Path(output_path)
    real_path = str(p.with_suffix(ext))
    Path(real_path).parent.mkdir(parents=True, exist_ok=True)
    with open(real_path, 'wb') as f:
        f.write(image_bytes)
    return real_path


class ImageGenerator:
    """Generate images from text prompts using Gemini via OpenRouter or Google AI"""

    def __init__(self):
        self.openrouter_key = OPENROUTER_API_KEY
        self.model = OPENROUTER_IMAGE_MODEL

    def generate_image(
        self,
        prompt: str,
        output_path: str,
        size: str = "1024x1024",
        quality: str = "standard",
    ) -> Optional[str]:
        """
        Generate an image from text prompt.

        Args:
            prompt: Text description for image generation
            output_path: Where to save the PNG image
            size: Image dimensions (1024x1024, 1024x768, 768x1024)
            quality: standard or high

        Returns:
            Path to generated image file, or None on failure
        """
        logger.info(f"[ImageGen] Generating image: {prompt[:60]}...")

        # Try OpenRouter first
        if self.openrouter_key:
            try:
                return self._generate_openrouter(prompt, output_path, size, quality)
            except Exception as e:
                logger.error(f"[ImageGen] OpenRouter failed: {e}")

        logger.error("[ImageGen] No valid API keys available")
        return None

    def _generate_openrouter(
        self, prompt: str, output_path: str, size: str, quality: str
    ) -> Optional[str]:
        """Generate image using OpenRouter API (Gemini 3.1 Flash Image Preview) via raw requests"""

        import json

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "HTTP-Referer": "https://ai-document-presentation.local",
            "X-Title": "AI Document Presentation",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()

            logger.debug(f"[ImageGen] Raw response keys: {list(data.keys())}")

            # Navigate to the message parts
            choices = data.get("choices", [])
            if not choices:
                raise ImageGeneratorError(f"No choices in response: {data}")

            message = choices[0].get("message", {})

            logger.debug(f"[ImageGen] Message keys: {list(message.keys())}")

            # 0) Check message['images'] - OpenRouter Gemini image response format
            # Format: [{'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,...'}}]
            images = message.get("images") or []
            if images:
                img = images[0]
                image_data = None
                if isinstance(img, str):
                    image_data = img
                elif isinstance(img, dict):
                    if img.get("type") == "image_url":
                        url_str = img.get("image_url", {}).get("url", "")
                    else:
                        url_str = img.get("url") or img.get("data") or img.get("b64_json") or ""
                    if url_str.startswith("data:image"):
                        image_data = url_str.split(",", 1)[1]
                    elif url_str.startswith("http"):
                        return self._download_image(url_str, output_path)
                    else:
                        image_data = url_str

                if image_data:
                    image_bytes = base64.b64decode(image_data)
                    real_path = _save_image(image_bytes, output_path)
                    logger.info(f"[ImageGen] Saved to {real_path}")
                    return real_path

            # 1) Try content_parts (multimodal format)
            parts = message.get("content_parts") or message.get("parts") or []

            # 2) Fallback: content as list (some OpenRouter responses)
            if not parts and isinstance(message.get("content"), list):
                parts = message["content"]

            image_data = None
            for part in parts:
                if isinstance(part, dict):
                    # inline_data format
                    if part.get("type") == "image_url":
                        url_str = part.get("image_url", {}).get("url", "")
                        if url_str.startswith("data:image"):
                            image_data = url_str.split(",", 1)[1]
                        elif url_str.startswith("http"):
                            return self._download_image(url_str, output_path)
                    elif "inline_data" in part:
                        image_data = part["inline_data"].get("data", "")
                    elif part.get("type") == "image" and "data" in part:
                        image_data = part["data"]

            # 3) Fallback: content as plain string
            if not image_data:
                content = message.get("content")
                if content and isinstance(content, str) and len(content) > 200:
                    if content.startswith("data:image"):
                        image_data = content.split(",", 1)[1]
                    elif content.startswith("http"):
                        return self._download_image(content, output_path)
                    else:
                        # Might be raw base64
                        image_data = content

            if not image_data:
                raise ImageGeneratorError(
                    f"No image data found in response. Message keys: {list(message.keys())}"
                )

            # Decode & save with correct extension
            image_bytes = base64.b64decode(image_data)
            real_path = _save_image(image_bytes, output_path)
            logger.info(f"[ImageGen] Saved to {real_path}")
            return real_path

        except Exception as e:
            raise ImageGeneratorError(f"OpenRouter image generation failed: {e}")

    def _generate_google(
        self, prompt: str, output_path: str, size: str, quality: str
    ) -> Optional[str]:
        """Generate image using Google AI (Imagen) API"""

        # Map size for Imagen
        size_map = {
            "1024x1024": "1024x1024",
            "1024x768": "1024x768",
            "768x1024": "768x1024",
        }
        google_size = size_map.get(size, "1024x1024")

        # Use Gemini 3.1 Flash Image model - this is the image generation model
        model_options = [
            "gemini-3.1-flash-image-preview",  # This is the image generation model
            "gemini-2.5-flash-image",  # Older experimental
            "gemini-2.0-flash-exp",  # Older experimental
        ]

        last_error = None
        for model in model_options:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.google_key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseModalities": ["image", "text"],
                        "temperature": 1,
                    },
                }
                response = requests.post(url, headers=headers, json=payload, timeout=60)

                if response.status_code == 200:
                    data = response.json()
                    # Check for image in parts
                    if "candidates" in data and data["candidates"]:
                        candidate = data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            for part in candidate["content"]["parts"]:
                                if "inlineData" in part:
                                    image_data = part["inlineData"]["data"]
                                    image_bytes = base64.b64decode(image_data)
                                    real_path = _save_image(image_bytes, output_path)
                                    logger.info(f"[ImageGen] Saved to {real_path}")
                                    return real_path

                    # Try alternative format
                    if "predictions" in data and data["predictions"]:
                        prediction = data["predictions"][0]
                        if "bytesBase64Encoded" in prediction:
                                image_data = prediction["bytesBase64Encoded"]
                                image_bytes = base64.b64decode(image_data)
                                real_path = _save_image(image_bytes, output_path)
                                logger.info(f"[ImageGen] Saved to {real_path}")
                                return real_path

                    last_error = f"No image in response: {data}"
                    continue
                else:
                    last_error = f"{response.status_code}: {response.text[:100]}"
                    continue
            except Exception as e:
                last_error = str(e)
                continue

        raise ImageGeneratorError(f"All models failed. Last error: {last_error}")

    def _download_image(self, url: str, output_path: str) -> str:
        """Download image from URL and save to output_path with correct extension."""
        response = requests.get(url, timeout=60)
        if response.status_code != 200:
            raise ImageGeneratorError(f"Download failed: {response.status_code}")

        real_path = _save_image(response.content, output_path)
        logger.info(f"[ImageGen] Downloaded to {real_path}")
        return real_path

    def generate_image_with_reference(
        self,
        prompt: str,
        reference_image_path: str,
        output_path: str,
    ) -> Optional[str]:
        """
        Generate an image using a reference image to lock position and lighting.

        Sends the reference image (IPS PNG) alongside the text prompt as a
        multimodal message so Gemini treats it as a visual anchor. This is used
        for the IPE (image_prompt_end) when use_start_as_ipe_reference is True
        on an object-evolution beat — it prevents LTX-2.3 from regenerating the
        subject from scratch and causes a true state-change transition instead.

        Args:
            prompt: The IPE text description
            reference_image_path: Absolute path to the IPS PNG already on disk
            output_path: Where to save the generated IPE image

        Returns:
            Path to generated image file, or None on failure
        """
        logger.info(f"[ImageGen] Generating IPE with IPS reference: {reference_image_path}")

        if not self.openrouter_key:
            logger.error("[ImageGen] No OpenRouter key — cannot generate with reference")
            return None

        try:
            # Read and encode the reference image as base64
            with open(reference_image_path, "rb") as f:
                ref_bytes = f.read()
            ref_b64 = base64.b64encode(ref_bytes).decode()

            # Detect MIME type from magic bytes
            ext = _detect_extension(ref_bytes)
            mime = "image/png" if ext == ".png" else ("image/webp" if ext == ".webp" else "image/jpeg")

            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.openrouter_key}",
                "HTTP-Referer": "https://ai-document-presentation.local",
                "X-Title": "AI Document Presentation",
                "Content-Type": "application/json",
            }

            # Multimodal message: reference image + IPE prompt
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{ref_b64}"},
                            },
                            {
                                "type": "text",
                                "text": (
                                    "The image above shows the protagonist of this story. "
                                    "Reproduce the SAME person with identical: face structure, "
                                    "skin tone, hair colour and style, and body type. "
                                    "The pose, expression, action, setting, and lighting "
                                    "may change freely to match the scene description below. "
                                    "Do NOT alter the person's fundamental appearance — "
                                    "only their situation and emotional state should change.\n\n"
                                    + prompt
                                ),
                            },
                        ],
                    }
                ],
            }

            import json
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()

            # Reuse the same response-parsing logic as the text-only path
            choices = data.get("choices", [])
            if not choices:
                raise ImageGeneratorError(f"No choices in reference response: {data}")

            message = choices[0].get("message", {})

            # Parse image from response (same logic as _generate_openrouter)
            images = message.get("images") or []
            if images:
                img = images[0]
                image_data = None
                if isinstance(img, str):
                    image_data = img
                elif isinstance(img, dict):
                    if img.get("type") == "image_url":
                        url_str = img.get("image_url", {}).get("url", "")
                    else:
                        url_str = img.get("url") or img.get("data") or img.get("b64_json") or ""
                    if url_str.startswith("data:image"):
                        image_data = url_str.split(",", 1)[1]
                    elif url_str.startswith("http"):
                        return self._download_image(url_str, output_path)
                    else:
                        image_data = url_str
                if image_data:
                    image_bytes = base64.b64decode(image_data)
                    real_path = _save_image(image_bytes, output_path)
                    logger.info(f"[ImageGen] IPE (with reference) saved to {real_path}")
                    return real_path

            parts = message.get("content_parts") or message.get("parts") or []
            if not parts and isinstance(message.get("content"), list):
                parts = message["content"]

            image_data = None
            for part in parts:
                if isinstance(part, dict):
                    if part.get("type") == "image_url":
                        url_str = part.get("image_url", {}).get("url", "")
                        if url_str.startswith("data:image"):
                            image_data = url_str.split(",", 1)[1]
                        elif url_str.startswith("http"):
                            return self._download_image(url_str, output_path)
                    elif "inline_data" in part:
                        image_data = part["inline_data"].get("data", "")
                    elif part.get("type") == "image" and "data" in part:
                        image_data = part["data"]

            if not image_data:
                content = message.get("content")
                if content and isinstance(content, str) and len(content) > 200:
                    if content.startswith("data:image"):
                        image_data = content.split(",", 1)[1]
                    elif content.startswith("http"):
                        return self._download_image(content, output_path)
                    else:
                        image_data = content

            if not image_data:
                raise ImageGeneratorError("No image data in reference-based response")

            image_bytes = base64.b64decode(image_data)
            real_path = _save_image(image_bytes, output_path)
            logger.info(f"[ImageGen] IPE (with reference) saved to {real_path}")
            return real_path

        except Exception as e:
            logger.warning(
                f"[ImageGen] Reference-based IPE generation failed: {e} — "
                f"falling back to text-only generation"
            )
            # Graceful fallback to standard text-only generation
            return self.generate_image(prompt, output_path)



def generate_image_for_beat(
    beat: dict,
    job_id: str,
    section_id: str,
    output_dir: str,
    reference_image_path: Optional[str] = None,
    image_provider: str = "gemini",
    image_model: str = "flux_dev",
    aspect_ratio: str = "16:9",
) -> Optional[str]:
    """
    Generate image for a single beat using the beat's image_prompt field.
    Used for: infographic beats and IPS (image_prompt_start) generation.

    Supports two providers:
      - "gemini" (default): Gemini 3.1 Flash via OpenRouter (cloud API)
      - "gpu": Local GPU via wan2gp-api (FLUX Dev / HiDream / etc.)

    Args:
        beat:                 Beat dict with image_prompt
        job_id:               Job ID for folder naming
        section_id:           Section ID for file naming
        output_dir:           Base output directory
        reference_image_path: Optional absolute path to a reference image.
                              When provided and file exists, uses Gemini multimodal
                              reference-based generation to lock character identity
                              (story mode). Defaults to None → text-only (no regression
                              for educational / V3 pipeline).
                              NOTE: auto-falls back to Gemini when gpu + reference is set,
                              because FLUX/HiDream don't support multimodal reference.
        image_provider:       "gemini" (cloud) or "gpu" (local GPU via wan2gp-api)
        image_model:          GPU model key: "flux_dev", "hidream_o1", "flux_schnell", etc.
                              Ignored when image_provider="gemini".
        aspect_ratio:         "16:9" | "9:16" | "1:1" — maps to resolution for local GPU.
                              Ignored when image_provider="gemini" (resolution is in prompt).

    Returns:
        Path to generated image (relative to output_dir), or None
    """
    image_prompt = beat.get("image_prompt", "")
    if not image_prompt:
        logger.warning(f"[ImageGen] No image_prompt in beat")
        return None

    # Create output path
    beat_id = beat.get("beat_id", f"beat_{section_id}")
    images_dir = Path(output_dir) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    output_path = str(images_dir / f"{job_id}_{beat_id}.png")

    # Determine generation strategy:
    # - reference provided + file exists → multimodal reference-based (story mode)
    # - otherwise → text-only (standard path, no regression)
    use_reference = (
        reference_image_path is not None
        and Path(reference_image_path).exists()
    )

    # STRICT PROVIDER MODE:
    #   "gpu"    → always text-only (FLUX/HiDream don't support reference images)
    #              reference is ignored regardless of what was passed in.
    #   "gemini" → reference used if available (story mode portrait locking).
    effective_provider = image_provider
    if image_provider == "gpu":
        use_reference = False   # force text-only — local GPU has no multimodal support

    MAX_RETRIES = 2
    abs_path = None
    for attempt in range(1 + MAX_RETRIES):
        if effective_provider == "gpu":
            # ── Local GPU path (FLUX / HiDream via wan2gp-api) ──────────
            from render.image.local_gpu_image_client import LocalGPUImageClient
            gpu_client = LocalGPUImageClient()
            abs_path = gpu_client.generate_image(
                prompt=image_prompt,
                output_path=output_path,
                model=image_model,
                aspect_ratio=aspect_ratio,
            )
        elif use_reference:
            # ── Gemini with reference image (story mode) ────────────────
            gen = ImageGenerator()
            abs_path = gen.generate_image_with_reference(
                prompt=image_prompt,
                reference_image_path=reference_image_path,
                output_path=output_path,
            )
        else:
            # ── Gemini text-only (standard path) ────────────────────────
            gen = ImageGenerator()
            abs_path = gen.generate_image(image_prompt, output_path)

        if abs_path is not None:
            if attempt > 0:
                logger.info(f"[ImageGen] Retry {attempt} succeeded for beat {beat_id}")
            break
        if attempt < MAX_RETRIES:
            logger.warning(
                f"[ImageGen] Attempt {attempt + 1} failed for beat {beat_id} "
                f"(provider={effective_provider}) — "
                f"retrying ({attempt + 1}/{MAX_RETRIES})..."
            )

    if abs_path is None:
        logger.error(
            f"[ImageGen] All {1 + MAX_RETRIES} attempts failed for beat {beat_id} "
            f"(provider={effective_provider})"
        )
        return None

    # Return relative path only for browser compatibility
    return os.path.join("images", os.path.basename(abs_path))


def generate_ipe_image(
    beat: dict,
    job_id: str,
    section_id: str,
    output_dir: str,
    ips_image_path: Optional[str] = None,
    image_provider: str = "gemini",
    image_model: str = "flux_dev",
) -> Optional[str]:
    """
    Generate the IPE (image_prompt_end) image for an image_to_video beat.

    When use_start_as_ipe_reference is True on the beat AND the IPS image file
    exists on disk, the IPS PNG is sent as a visual reference to Gemini so the
    generated IPE has the same subject position, orientation, and lighting —
    preventing LTX-2.3 from regenerating the subject from scratch.

    Falls back to standard text-only generation if:
      - use_start_as_ipe_reference is false / absent (default behaviour, no change)
      - ips_image_path is None or the file does not exist yet
      - the reference-based call raises an exception

    Args:
        beat: Beat dict with image_prompt_end and optionally use_start_as_ipe_reference
        job_id: Job ID for folder naming
        section_id: Section ID for file naming
        output_dir: Base output directory
        ips_image_path: Absolute path to the already-generated IPS image, or None
        image_provider: "gemini" (cloud) or "gpu" (local GPU via wan2gp-api)
        image_model: GPU model key (ignored when image_provider="gemini")

    Returns:
        Path to generated IPE image (relative to output_dir), or None
    """
    image_prompt = beat.get("image_prompt_end", "")
    if not image_prompt:
        logger.warning(f"[ImageGen] No image_prompt_end in beat")
        return None

    beat_id = beat.get("beat_id", f"beat_{section_id}")
    images_dir = Path(output_dir) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(images_dir / f"{job_id}_{beat_id}_ipe.png")

    abs_path: Optional[str] = None

    # ── Local GPU path (FLUX / HiDream) ─────────────────────────────────────
    if image_provider == "gpu":
        from render.image.local_gpu_image_client import LocalGPUImageClient
        gpu_client = LocalGPUImageClient()
        abs_path = gpu_client.generate_image(
            prompt=image_prompt,
            output_path=output_path,
            model=image_model,
        )
        if abs_path is None:
            logger.error(f"[ImageGen] IPE GPU generation failed for beat {beat_id}")
            return None
        return os.path.join("images", os.path.basename(abs_path))

    # ── Gemini path (cloud) ──────────────────────────────────────────────────
    use_reference = beat.get("use_start_as_ipe_reference", False)
    gen = ImageGenerator()

    if use_reference and ips_image_path and Path(ips_image_path).exists():
        logger.info(
            f"[ImageGen] Beat {beat_id}: use_start_as_ipe_reference=true "
            f"— generating IPE with IPS reference {Path(ips_image_path).name}"
        )
        abs_path = gen.generate_image_with_reference(
            prompt=image_prompt,
            reference_image_path=ips_image_path,
            output_path=output_path,
        )
    else:
        if use_reference and not (ips_image_path and Path(ips_image_path).exists()):
            logger.warning(
                f"[ImageGen] Beat {beat_id}: use_start_as_ipe_reference=true "
                f"but IPS file not found — falling back to text-only IPE generation"
            )
        abs_path = gen.generate_image(image_prompt, output_path)

    if abs_path is None:
        logger.error(f"[ImageGen] IPE generation failed for beat {beat_id}")
        return None

    return os.path.join("images", os.path.basename(abs_path))
