"""
Smart Chunker v1.4 - Pass 0: Topic Extraction

Extracts logical topic blocks from markdown with metadata for downstream Directors.
Uses Gemini 2.5 Pro with structured output (JSON schema enforcement).
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from openai import OpenAI

from core.json_repair import repair_and_parse_json, validate_json_structure
from core.analytics import AnalyticsTracker

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL
)

PROMPTS_DIR = Path(__file__).parent / "prompts"
SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"

MODEL = "google/gemini-2.5-pro"

MAX_STRUCTURAL_RETRIES = 2

SMART_CHUNKER_SCHEMA = {
    "type": "object",
    "properties": {
        "source_topic": {
            "type": "string",
            "description": "The main subject matter of the provided text"
        },
        "topics": {
            "type": "array",
            "description": "List of logical sub-topics extracted from the text",
            "items": {
                "type": "object",
                "properties": {
                    "topic_id": {"type": "string"},
                    "title": {"type": "string"},
                    "concept_type": {
                        "type": "string",
                        "enum": ["process", "definition", "example", "formula", "theory", "fact"]
                    },
                    "source_blocks": {
                        "type": "array",
                        "items": {"type": "integer"}
                    },
                    "key_terms": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "has_formula": {"type": "boolean"},
                    "suggested_renderer": {
                        "type": "string",
                        "enum": ["remotion", "manim", "video"]
                    }
                },
                "required": ["topic_id", "title", "concept_type", "source_blocks", "suggested_renderer"]
            }
        }
    },
    "required": ["source_topic", "topics"]
}


def load_prompt(name: str) -> str:
    """Load a prompt file."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, "r") as f:
        return f.read()


def call_smart_chunker(
    markdown_content: str,
    subject: str,
    tracker: Optional[AnalyticsTracker] = None,
    max_retries: int = MAX_STRUCTURAL_RETRIES
) -> Dict:
    """
    PASS 0: Extract logical topics from markdown.
    Uses Gemini 2.5 Pro with JSON schema enforcement.
    
    Args:
        markdown_content: Raw markdown content from document
        subject: Subject area (e.g., "Biology", "Physics")
        tracker: Analytics tracker for cost/time logging
        max_retries: Maximum structural retries (default 2)
        
    Returns:
        Dict with source_topic and topics array
        
    Raises:
        ChunkerError: If chunking fails after all retries
    """
    logger.info(f"[Smart Chunker] Starting topic extraction for {subject}")
    
    system_prompt = load_prompt("smart_chunker_system_v1.4")
    user_prompt_template = load_prompt("smart_chunker_user_v1.4")
    
    numbered_content = _add_block_numbers(markdown_content)
    
    user_prompt = user_prompt_template.format(
        subject=subject,
        markdown_content=numbered_content
    )
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            if tracker:
                tracker.start_phase("smart_chunker", MODEL)
            
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=8192,
                response_format={"type": "json_object"}
            )
            
            raw_response = response.choices[0].message.content or ""
            
            if not raw_response:
                raise ChunkerError("Empty response from LLM")
            
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            
            if tracker:
                tracker.end_phase("smart_chunker", input_tokens, output_tokens)
            
            result = repair_and_parse_json(raw_response)
            
            errors = _validate_chunker_output(result)
            if errors:
                raise ChunkerValidationError(errors)
            
            logger.info(f"[Smart Chunker] Successfully extracted {len(result.get('topics', []))} topics")
            return result
            
        except (json.JSONDecodeError, ChunkerValidationError) as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(f"[Smart Chunker] Retry {attempt + 1}/{max_retries}: {e}")
                user_prompt = _get_retry_prompt(user_prompt, str(e))
            else:
                logger.error(f"[Smart Chunker] Failed after {max_retries} retries: {e}")
        
        except Exception as e:
            logger.error(f"[Smart Chunker] Unexpected error: {e}")
            raise ChunkerError(f"Unexpected error in Smart Chunker: {e}")
    
    raise ChunkerError(f"Smart Chunker failed after {max_retries} retries: {last_error}")


def _add_block_numbers(content: str) -> str:
    """Add block numbers to markdown content for reference."""
    lines = content.split('\n')
    numbered = []
    block_num = 0
    in_block = False
    
    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('#') or stripped.startswith('##') or stripped.startswith('###'):
            block_num += 1
            numbered.append(f"[BLOCK {block_num}]")
            numbered.append(line)
            in_block = True
        elif stripped and not in_block:
            block_num += 1
            numbered.append(f"[BLOCK {block_num}]")
            numbered.append(line)
            in_block = True
        elif stripped:
            numbered.append(line)
        else:
            numbered.append(line)
            in_block = False
    
    return '\n'.join(numbered)


def _validate_chunker_output(data: Dict) -> List[str]:
    """Validate chunker output structure and content."""
    errors = []
    
    missing = validate_json_structure(data, ["source_topic", "topics"])
    if missing:
        errors.append(f"Missing required fields: {missing}")
    
    topics = data.get("topics", [])
    if not topics:
        errors.append("topics array is empty")
    
    for i, topic in enumerate(topics):
        topic_errors = _validate_topic(topic, i)
        errors.extend(topic_errors)
    
    return errors


def _validate_topic(topic: Dict, index: int) -> List[str]:
    """Validate a single topic entry."""
    errors = []
    prefix = f"topics[{index}]"
    
    required = ["topic_id", "title", "concept_type", "source_blocks", "suggested_renderer"]
    for field in required:
        if field not in topic:
            errors.append(f"{prefix}: missing required field '{field}'")
    
    valid_types = ["process", "definition", "example", "formula", "theory", "fact"]
    if topic.get("concept_type") and topic["concept_type"] not in valid_types:
        errors.append(f"{prefix}: invalid concept_type '{topic['concept_type']}'")
    
    valid_renderers = ["remotion", "manim", "video"]
    if topic.get("suggested_renderer") and topic["suggested_renderer"] not in valid_renderers:
        errors.append(f"{prefix}: invalid suggested_renderer '{topic['suggested_renderer']}'")
    
    return errors


def _get_retry_prompt(original_prompt: str, error_message: str) -> str:
    """Generate retry prompt with specific error feedback."""
    retry_addition = f"""

---
RETRY REQUIRED: Your previous response had the following errors:
{error_message}

Please fix these issues and output valid JSON matching the required schema.
Ensure all required fields are present: source_topic, topics array with topic_id, title, concept_type, source_blocks, suggested_renderer.
---

"""
    return original_prompt + retry_addition


class ChunkerError(Exception):
    """Error raised when Smart Chunker fails."""
    pass


class ChunkerValidationError(Exception):
    """Error raised when Smart Chunker output fails validation."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Validation errors: {', '.join(errors)}")
