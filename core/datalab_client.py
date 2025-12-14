import os
import requests
from pathlib import Path
from pypdf import PdfReader

DATALAB_API_KEY = os.environ.get("DATALAB_API_KEY", "")
DATALAB_API_URL = "https://api.datalab.to/api/v1/marker"

def pdf_to_markdown(pdf_path: str) -> str:
    if DATALAB_API_KEY:
        try:
            return _convert_with_datalab(pdf_path)
        except Exception as e:
            print(f"Datalab API failed: {e}, using local extraction")
            return _local_pdf_extraction(pdf_path)
    else:
        return _local_pdf_extraction(pdf_path)

def _convert_with_datalab(pdf_path: str) -> str:
    with open(pdf_path, "rb") as f:
        files = {"file": (Path(pdf_path).name, f, "application/pdf")}
        headers = {"X-Api-Key": DATALAB_API_KEY}
        
        response = requests.post(
            DATALAB_API_URL,
            files=files,
            headers=headers,
            data={"output_format": "markdown"}
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("markdown", result.get("text", ""))
        else:
            raise Exception(f"Datalab API error: {response.status_code} - {response.text}")

def _local_pdf_extraction(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text_parts = []
    
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    
    full_text = "\n\n".join(text_parts)
    
    filename = Path(pdf_path).stem
    lines = full_text.split('\n')
    markdown_lines = [f"# {filename}\n"]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.isupper() and len(line) > 3:
            markdown_lines.append(f"\n## {line.title()}\n")
        elif line.endswith(':') and len(line) < 60:
            markdown_lines.append(f"\n### {line[:-1]}\n")
        else:
            markdown_lines.append(line)
    
    return "\n".join(markdown_lines)
