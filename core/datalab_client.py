import os
import time
import requests
from pathlib import Path
from typing import Dict, Any, Tuple

DATALAB_API_KEY = os.environ.get("DATALAB_API_KEY", "")
DATALAB_API_URL = "https://api.datalab.to/api/v1/marker"
MIN_MARKDOWN_LENGTH = 100
MAX_POLL_TIME = 1200
POLL_INTERVAL = 3

# ISS-206: Datalab supports these file types
SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.odt'}

# Local OCR (Marker-compatible) — optional fallback
LOCAL_OCR_URL = os.environ.get("LOCAL_OCR_URL", "")
LOCAL_OCR_API_URL = f"{LOCAL_OCR_URL.rstrip('/')}/extract" if LOCAL_OCR_URL else ""
LOCAL_OCR_POLL_URL = f"{LOCAL_OCR_URL.rstrip('/')}/status" if LOCAL_OCR_URL else ""


class DatalabConversionError(Exception):
    """Raised when Datalab PDF conversion fails - NO fallback allowed."""
    pass


class ConversionResult:
    """ISS-207: Result object with markdown and metadata (page_count, images, etc)."""
    def __init__(self, markdown: str, page_count: int = 0, metadata: Dict[str, Any] = None, images: Dict[str, str] = None):
        self.markdown = markdown
        self.page_count = page_count
        self.metadata = metadata or {}
        self.images = images or {}  # Dict of filename -> base64 data
    
    def __str__(self):
        return self.markdown


def _convert_with_local_ocr(file_path: str) -> ConversionResult:
    """Convert file using local Marker-compatible OCR server at LOCAL_OCR_URL.
    
    Same API format as Datalab: POST multipart with output_format=markdown.
    No API key header needed.
    Returns ConversionResult or raises DatalabConversionError on failure.
    """
    try:
        filename = Path(file_path).name
        mime_type = get_mime_type(file_path)
        
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, mime_type)}
            
            print(f"[Local OCR] Submitting document: {file_path} (type: {mime_type}) to {LOCAL_OCR_API_URL}")
            response = requests.post(
                LOCAL_OCR_API_URL,
                files=files,
                data={"output_format": "markdown"},
                timeout=120
            )
            
            if response.status_code not in (200, 202):
                raise DatalabConversionError(
                    f"Local OCR API error: {response.status_code} - {response.text[:500]}"
                )
            
            result = response.json()
            
            # Check for async task ID first
            task_id = result.get("task_id")
            if task_id:
                check_url = f"{LOCAL_OCR_POLL_URL}/{task_id}"
                print(f"[Local OCR] Polling for results: {check_url}")
                return _poll_for_result(check_url, is_local=True)
            
            # Extract page_count from response
            metadata = result.get("metadata", {})
            page_count = result.get("page_count", 0)
            if not page_count:
                page_count = metadata.get("page_count", metadata.get("total_pages", 0))
            
            # Extract images dict from response (base64 encoded)
            images = result.get("images", {})
            if images:
                print(f"[Local OCR] Found {len(images)} images in response")
            
            # Local OCR (synchronous mode) returns: {"success":true,"format":"markdown","output":"..."}
            if result.get("output"):
                return ConversionResult(
                    markdown=result["output"],
                    page_count=page_count,
                    metadata={"source": "local_immediate"},
                    images=images
                )
            
            if result.get("markdown"):
                return ConversionResult(
                    markdown=result["markdown"],
                    page_count=page_count,
                    metadata={"source": "local_immediate"},
                    images=images
                )
            if result.get("text"):
                return ConversionResult(
                    markdown=result["text"],
                    page_count=page_count,
                    metadata={"source": "local_immediate_text"},
                    images=images
                )
            
            # async mode (if server still supports it): {"status":"processing","user_id":"conv_xxx"}
            user_id = result.get("user_id")
            check_url = result.get("request_check_url")
            if check_url:
                print(f"[Local OCR] Polling for results: {check_url}")
                return _poll_for_result(check_url)
            if user_id and LOCAL_OCR_URL:
                status_url = f"{LOCAL_OCR_URL.rstrip('/')}/api/status/{user_id}"
                print(f"[Local OCR] Polling for results: {status_url} (user_id: {user_id})")
                return _poll_for_result(status_url)
            
            raise DatalabConversionError(
                f"Local OCR returned no markdown and no check URL: {result}"
            )
            
    except requests.exceptions.RequestException as e:
        raise DatalabConversionError(f"Local OCR API request failed: {e}")


def is_supported_file(filename: str) -> bool:
    """ISS-206: Check if file extension is supported by Datalab."""
    ext = Path(filename).suffix.lower()
    return ext in SUPPORTED_EXTENSIONS


def get_mime_type(filename: str) -> str:
    """ISS-206: Get MIME type for supported file types."""
    ext = Path(filename).suffix.lower()
    mime_types = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.odt': 'application/vnd.oasis.opendocument.text'
    }
    return mime_types.get(ext, 'application/octet-stream')


def document_to_markdown(file_path: str, ocr_provider: str = "local") -> ConversionResult:
    """ISS-206: Convert PDF/DOC/DOCX/ODT to markdown using specified OCR provider.
    
    If ocr_provider is 'local', it strictly uses the local marker API.
    If ocr_provider is 'datalab', it strictly uses the Datalab API.
    Raises DatalabConversionError if the chosen source is not configured or fails.
    
    Returns:
        ConversionResult with markdown text and metadata (page_count, etc)
    """
    if not is_supported_file(file_path):
        ext = Path(file_path).suffix
        raise DatalabConversionError(
            f"Unsupported file type: {ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    
    if ocr_provider == "local":
        if not LOCAL_OCR_URL:
            raise DatalabConversionError("Local OCR provider selected, but LOCAL_OCR_URL is not configured.")
        result = _convert_with_local_ocr(file_path)
    elif ocr_provider == "datalab":
        if not DATALAB_API_KEY:
            raise DatalabConversionError("Datalab OCR provider selected, but DATALAB_API_KEY is not configured.")
        result = _convert_with_datalab(file_path)
    else:
        # Fallback if unknown provider specified
        if LOCAL_OCR_URL:
            result = _convert_with_local_ocr(file_path)
        elif DATALAB_API_KEY:
            result = _convert_with_datalab(file_path)
        else:
            raise DatalabConversionError(
                f"Unknown ocr_provider '{ocr_provider}' and neither LOCAL_OCR_URL nor DATALAB_API_KEY configured."
            )
    
    if len(result.markdown) < MIN_MARKDOWN_LENGTH:
        raise DatalabConversionError(
            f"OCR returned insufficient content ({len(result.markdown)} chars). "
            f"Minimum required: {MIN_MARKDOWN_LENGTH} chars. "
            "Document may be image-only or corrupted."
        )
    
    return result


def pdf_to_markdown(pdf_path: str, ocr_provider: str = "local") -> str:
    """Legacy function - Convert PDF to markdown.
    
    FAIL-FAST: Raises DatalabConversionError if:
    - Provider not configured
    - API request fails
    - Returned markdown is less than MIN_MARKDOWN_LENGTH chars
    """
    result = document_to_markdown(pdf_path, ocr_provider=ocr_provider)
    return result.markdown

def _convert_with_datalab(file_path: str) -> ConversionResult:
    """ISS-206/207: Call Datalab API to convert PDF/DOC/DOCX/ODT to markdown.
    
    Datalab uses async processing - submit file, then poll for results.
    Returns ConversionResult with markdown and page_count.
    """
    try:
        filename = Path(file_path).name
        mime_type = get_mime_type(file_path)
        
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, mime_type)}
            headers = {"X-Api-Key": DATALAB_API_KEY}
            
            print(f"[Datalab] Submitting document: {file_path} (type: {mime_type})")
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
            
            # ISS-207: Extract page_count from response
            page_count = result.get("page_count", 0)
            
            # Extract images dict from response (base64 encoded)
            images = result.get("images", {})
            if images:
                print(f"[Datalab] Found {len(images)} images in response")
            
            if result.get("markdown"):
                return ConversionResult(
                    markdown=result["markdown"],
                    page_count=page_count,
                    metadata={"source": "immediate"},
                    images=images
                )
            if result.get("text"):
                return ConversionResult(
                    markdown=result["text"],
                    page_count=page_count,
                    metadata={"source": "immediate_text"},
                    images=images
                )
            
            check_url = result.get("request_check_url")
            if not check_url:
                raise DatalabConversionError(
                    f"Datalab returned no markdown and no check URL: {result}"
                )
            
            print(f"[Datalab] Polling for results: {check_url}")
            return _poll_for_result(check_url, is_local=False)
            
    except requests.exceptions.RequestException as e:
        raise DatalabConversionError(f"Datalab API request failed: {e}")


def _poll_for_result(check_url: str, is_local: bool = False) -> ConversionResult:
    """ISS-207: Poll API until conversion is complete. Returns ConversionResult."""
    elapsed = 0
    
    api_source = "Local OCR" if is_local else "Datalab"
    poll_headers = {} if is_local else {"X-Api-Key": DATALAB_API_KEY}
    
    while elapsed < MAX_POLL_TIME:
        try:
            response = requests.get(
                check_url,
                headers=poll_headers,
                timeout=30
            )
            
            if response.status_code != 200:
                raise DatalabConversionError(
                    f"{api_source} poll failed: {response.status_code} - {response.text[:200]}"
                )
            
            result = response.json()
            status = result.get("status", "unknown")
            page_count = result.get("page_count", 0)
            print(f"[{api_source}] Status: {status}, Pages: {page_count} (elapsed: {elapsed}s)")
            
            # BUG FIX: local marker API returns "completed" (with 'd'), Datalab returns "complete"
            if status in ("complete", "completed"):
                # BUG FIX: local marker API returns markdown under "markdown_output" key;
                # Datalab uses "markdown"; fallback to "text" or "output"
                markdown = (
                    result.get("markdown_output")
                    or result.get("markdown")
                    or result.get("output")
                    or result.get("text")
                    or ""
                )
                images = result.get("images", {})
                if images:
                    print(f"[{api_source}] Found {len(images)} images in polled response")
                if markdown:
                    print(f"[{api_source}] SUCCESS: {len(markdown)} chars, {page_count} pages, {len(images)} images")
                    return ConversionResult(
                        markdown=markdown,
                        page_count=page_count,
                        images=images,
                        metadata={"source": "polled"}
                    )
                raise DatalabConversionError(f"{api_source} completed but returned no content")
            
            if status == "error" or status == "failed":
                error_msg = result.get("error", "Unknown error")
                raise DatalabConversionError(f"{api_source} conversion failed: {error_msg}")
            
            time.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
            
        except requests.exceptions.RequestException as e:
            raise DatalabConversionError(f"{api_source} poll request failed: {e}")
    
    raise DatalabConversionError(f"{api_source} conversion timed out after {MAX_POLL_TIME}s")
