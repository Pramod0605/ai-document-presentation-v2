import os
import requests
from pathlib import Path

DATALAB_API_KEY = os.environ.get("DATALAB_API_KEY", "")
DATALAB_API_URL = "https://api.datalab.to/api/v1/marker"
MIN_MARKDOWN_LENGTH = 100


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
    """Call Datalab API to convert PDF to markdown."""
    try:
        with open(pdf_path, "rb") as f:
            files = {"file": (Path(pdf_path).name, f, "application/pdf")}
            headers = {"X-Api-Key": DATALAB_API_KEY}
            
            response = requests.post(
                DATALAB_API_URL,
                files=files,
                headers=headers,
                data={"output_format": "markdown"},
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("markdown", result.get("text", ""))
            else:
                raise DatalabConversionError(
                    f"Datalab API error: {response.status_code} - {response.text[:500]}"
                )
    except requests.exceptions.RequestException as e:
        raise DatalabConversionError(f"Datalab API request failed: {e}")
