"""
core/utils/markdown_cleaner.py

Strips binary/base64 blobs from OCR-produced markdown before passing to
any LLM agent.

Free/local OCR servers (e.g. the local Datalab-compatible server) embed
the raw scanned page as a data-URI inside a markdown image tag:

    ![](data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/...)

This can inflate a single-page document to ~90,000 characters of binary
garbage, causing every downstream LLM call to fail or return garbage.

Usage:
    from core.utils.markdown_cleaner import clean_markdown_for_llm
    markdown = clean_markdown_for_llm(markdown, label="V3 Job abc123")
"""

import re
import sys
from typing import Optional


def clean_markdown_for_llm(markdown: str, label: Optional[str] = None) -> str:
    """
    Strip embedded binary/base64 content from OCR-produced markdown.

    Handles:
    1. Markdown image tags with data-URI base64 payloads:
           ![alt](data:image/jpeg;base64,<BLOB>)
    2. Bare base64 blobs on their own lines (>500 chars, only base64 chars).

    Each removed blob is replaced with a compact ``[IMAGE]`` placeholder so
    the LLM still knows an image existed at that position in the document.

    Args:
        markdown:  Raw markdown string from the OCR pipeline.
        label:     Optional prefix for the log message (e.g. job id).

    Returns:
        Cleaned markdown string safe to pass to an LLM.
    """
    if not markdown:
        return markdown

    original_len = len(markdown)

    # ── 1. Strip markdown image tags that carry a data-URI base64 payload ────
    # Matches: ![any alt text](data:image/TYPE;base64,BASE64DATA)
    # The base64 payload may span multiple lines (re.DOTALL).
    cleaned = re.sub(
        r'!\[([^\]]*)\]\(\s*data:[^;]+;base64,[A-Za-z0-9+/=\s]+\s*\)',
        lambda m: f'[IMAGE: {m.group(1)}]' if m.group(1).strip() else '[IMAGE]',
        markdown,
        flags=re.DOTALL,
    )

    # ── 2. Strip bare base64 blobs on their own lines ────────────────────────
    # A "bare base64 line" is one that:
    #   - Is longer than 500 characters after stripping whitespace
    #   - Consists entirely of base64 alphabet characters (A-Z a-z 0-9 + / =)
    # These appear when the OCR response puts raw base64 outside an image tag.
    lines = cleaned.split('\n')
    result_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 500 and re.fullmatch(r'[A-Za-z0-9+/=]+', stripped):
            result_lines.append('[IMAGE]')
        else:
            result_lines.append(line)
    cleaned = '\n'.join(result_lines)

    # ── 3. Collapse 3+ consecutive blank lines down to 2 ─────────────────────
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = cleaned.strip()

    removed = original_len - len(cleaned)
    if removed > 0:
        tag = f"[{label}] " if label else ""
        print(
            f"{tag}clean_markdown_for_llm: stripped {removed:,} chars of base64/image data "
            f"({original_len:,} → {len(cleaned):,} chars). "
            f"LLM will see clean text with [IMAGE] placeholder(s).",
            flush=True,
        )

    return cleaned
