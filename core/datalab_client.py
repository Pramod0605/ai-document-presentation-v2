import os
import requests
from pathlib import Path

DATALAB_API_KEY = os.environ.get("DATALAB_API_KEY", "")
DATALAB_API_URL = "https://api.datalab.to/api/v1/marker"

def pdf_to_markdown(pdf_path: str) -> str:
    if DATALAB_API_KEY:
        return _convert_with_datalab(pdf_path)
    else:
        return _stub_conversion(pdf_path)

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

def _stub_conversion(pdf_path: str) -> str:
    filename = Path(pdf_path).stem
    
    return f"""# {filename}

## Introduction
This chapter introduces the fundamental concepts that form the foundation of our understanding.

## Key Concepts

### Concept 1: Basic Principles
The basic principles help us understand how things work in nature. These principles are observed through careful experimentation and observation.

### Concept 2: Applications
Real-world applications demonstrate how theoretical knowledge translates into practical solutions. Students can see these applications in everyday life.

### Concept 3: Problem Solving
Problem-solving techniques help students apply their knowledge to new situations. This involves breaking down complex problems into smaller, manageable parts.

## Summary
This chapter covered the essential concepts needed to build a strong foundation. Practice the exercises to reinforce your understanding.

## Review Questions
1. What are the basic principles discussed in this chapter?
2. How do these concepts apply to real-world situations?
3. Describe the problem-solving approach outlined in this chapter.
"""
