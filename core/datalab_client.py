import os
import time
import requests
from pathlib import Path

DATALAB_API_KEY = os.environ.get("DATALAB_API_KEY", "")
DATALAB_API_URL = "https://api.datalab.to/api/v1/marker"
MIN_MARKDOWN_LENGTH = 100
MAX_POLL_TIME = 300
POLL_INTERVAL = 3


class DatalabConversionError(Exception):
    """Raised when Datalab PDF conversion fails - NO fallback allowed."""
    pass


def pdf_to_markdown(pdf_path: str) -> str:
    """Convert PDF to markdown using Datalab API.
    
    FAIL-FAST: No fallback to local extraction. Raises DatalabConversionError if:
    - DATALAB_API_KEY not configured
    - API request fails
    - Returned markdown is less than MIN_MARKDOWN_LENGTH chars
    """
    if not DATALAB_API_KEY:
        raise DatalabConversionError(
            "DATALAB_API_KEY not configured. PDF conversion requires Datalab API."
        )
    
    markdown = _convert_with_datalab(pdf_path)
    
    if len(markdown) < MIN_MARKDOWN_LENGTH:
        raise DatalabConversionError(
            f"Datalab returned insufficient content ({len(markdown)} chars). "
            f"Minimum required: {MIN_MARKDOWN_LENGTH} chars. "
            "PDF may be image-only or corrupted."
        )
    
    return markdown

def _convert_with_datalab(pdf_path: str) -> str:
    """Call Datalab API to convert PDF to markdown.
    
    Datalab uses async processing - submit file, then poll for results.
    """
    try:
        with open(pdf_path, "rb") as f:
            files = {"file": (Path(pdf_path).name, f, "application/pdf")}
            headers = {"X-Api-Key": DATALAB_API_KEY}
            
            print(f"[Datalab] Submitting PDF: {pdf_path}")
            response = requests.post(
                DATALAB_API_URL,
                files=files,
                headers=headers,
                data={"output_format": "markdown"},
                timeout=120
            )
            
            if response.status_code != 200:
                raise DatalabConversionError(
                    f"Datalab API error: {response.status_code} - {response.text[:500]}"
                )
            
            result = response.json()
            
            if result.get("markdown"):
                return result["markdown"]
            if result.get("text"):
                return result["text"]
            
            check_url = result.get("request_check_url")
            if not check_url:
                raise DatalabConversionError(
                    f"Datalab returned no markdown and no check URL: {result}"
                )
            
            print(f"[Datalab] Polling for results: {check_url}")
            return _poll_for_result(check_url)
            
    except requests.exceptions.RequestException as e:
        raise DatalabConversionError(f"Datalab API request failed: {e}")


def _poll_for_result(check_url: str) -> str:
    """Poll Datalab API until conversion is complete."""
    elapsed = 0
    
    while elapsed < MAX_POLL_TIME:
        try:
            response = requests.get(
                check_url,
                headers={"X-Api-Key": DATALAB_API_KEY},
                timeout=30
            )
            
            if response.status_code != 200:
                raise DatalabConversionError(
                    f"Datalab poll failed: {response.status_code} - {response.text[:200]}"
                )
            
            result = response.json()
            status = result.get("status", "unknown")
            print(f"[Datalab] Status: {status} (elapsed: {elapsed}s)")
            
            if status == "complete":
                markdown = result.get("markdown", result.get("text", ""))
                if markdown:
                    print(f"[Datalab] SUCCESS: {len(markdown)} chars received")
                    return markdown
                raise DatalabConversionError("Datalab completed but returned no content")
            
            if status == "error" or status == "failed":
                error_msg = result.get("error", "Unknown error")
                raise DatalabConversionError(f"Datalab conversion failed: {error_msg}")
            
            time.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
            
        except requests.exceptions.RequestException as e:
            raise DatalabConversionError(f"Datalab poll request failed: {e}")
    
    raise DatalabConversionError(f"Datalab conversion timed out after {MAX_POLL_TIME}s")
