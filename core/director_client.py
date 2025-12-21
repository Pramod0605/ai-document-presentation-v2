"""
Director Client v1.3 - Deterministic Educational Film Engine

This module handles the Director LLM pass with:
- Strict Gemini 2.5 Pro parameter tuning (low temperature, high determinism)
- Schema validation after each attempt
- Retry logic with structure-repair-only prompts
- Hard fail after 2 retries (no fallbacks, no normalization repair)

Pipeline role:
- Pass 1: Director (this module)
- Takes chunked content from Pass 0 (Chunker)
- Outputs presentation.json conforming to v1.3 schema
"""

import os
import sys
import json
import re
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from core.analytics import AnalyticsTracker, create_tracker
from core.traceability import save_raw_llm_response
from core.schema_validator import (
    validate_presentation,
    quick_structure_check,
    format_errors_for_retry
)


def log(msg: str):
    print(msg)
    sys.stdout.flush()


OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL
)

PROMPTS_DIR = Path(__file__).parent / "prompts"

DIRECTOR_MODEL = "anthropic/claude-3.5-sonnet"

DIRECTOR_PARAMS = {
    "temperature": 0.2,
    "top_p": 0.9,
    "max_tokens": 8192,
}

MAX_RETRIES = 2


class DirectorError(Exception):
    """Error raised when Director fails after all retries."""
    def __init__(self, message: str, errors: List[str], attempts: int):
        super().__init__(message)
        self.errors = errors
        self.attempts = attempts


def load_prompt(name: str) -> str:
    """Load a prompt file. v1.3 prompts required."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        v13_path = PROMPTS_DIR / f"{name}_v1.3.txt"
        if v13_path.exists():
            path = v13_path
        else:
            raise FileNotFoundError(f"Prompt file not found: {path}")
    
    with open(path, "r") as f:
        return f.read()


def fix_json(text: str) -> str:
    """Clean up LLM JSON output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    
    return text


def parse_json_response(text: str) -> Dict:
    """Parse JSON from LLM response."""
    try:
        fixed = fix_json(text)
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        log(f"[Director] JSON parse error: {e}")
        log(f"[Director] Raw text (first 500 chars): {text[:500]}")
        raise


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def call_director_llm(
    system_prompt: str,
    user_prompt: str,
    tracker: Optional[AnalyticsTracker] = None,
    phase_name: str = "director"
) -> Tuple[str, Dict]:
    """Make a Director LLM call with retry and optimized parameters."""
    
    if tracker:
        tracker.start_phase(phase_name, DIRECTOR_MODEL)
    
    try:
        response = client.chat.completions.create(
            model=DIRECTOR_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=DIRECTOR_PARAMS["temperature"],
            top_p=DIRECTOR_PARAMS["top_p"],
            max_tokens=DIRECTOR_PARAMS["max_tokens"],
        )
        
        content = response.choices[0].message.content or ""
        usage = {
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0
        }
        
        if tracker:
            tracker.end_phase(phase_name, usage["input_tokens"], usage["output_tokens"])
        
        return content, usage
        
    except Exception as e:
        if tracker:
            tracker.end_phase(phase_name, 0, 0, status="failed", error=str(e))
        raise


def run_director(
    chunks: Dict,
    subject: str,
    grade: str,
    chapter: str = "",
    tracker: Optional[AnalyticsTracker] = None,
    job_id: Optional[str] = None
) -> Dict:
    """
    Run the Director pass with schema validation and retry logic.
    
    This is the main entry point for Pass 1.
    
    Args:
        chunks: Output from Pass 0 (Chunker)
        subject: Subject name (e.g., "Physics")
        grade: Grade level (e.g., "9")
        chapter: Chapter title
        tracker: Analytics tracker (optional)
        job_id: Job ID for traceability (optional)
    
    Returns:
        Validated presentation dict conforming to v1.3 schema
        
    Raises:
        DirectorError: If validation fails after MAX_RETRIES attempts
    """
    log("[Director] Starting Director pass (v1.3)...")
    log(f"[Director] Model: {DIRECTOR_MODEL}")
    log(f"[Director] Params: temp={DIRECTOR_PARAMS['temperature']}, top_p={DIRECTOR_PARAMS['top_p']}")
    
    system_prompt = load_prompt("director_system_v1.3")
    user_template = load_prompt("director_user_v1.3")
    
    chunks_json = json.dumps(chunks, indent=2)
    
    user_prompt = user_template.replace("{subject}", subject)
    user_prompt = user_prompt.replace("{grade}", str(grade))
    user_prompt = user_prompt.replace("{chapter}", chapter or "Educational Content")
    user_prompt = user_prompt.replace("{chunks_json}", chunks_json)
    user_prompt = user_prompt.replace("{markdown_content}", chunks_json)
    
    response_text, usage = call_director_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tracker=tracker,
        phase_name="director_attempt_1"
    )
    
    if job_id:
        save_raw_llm_response(
            renderer_type="director",
            section_id="attempt_1",
            raw_response=response_text,
            model=DIRECTOR_MODEL,
            usage=usage
        )
    
    try:
        presentation = parse_json_response(response_text)
    except json.JSONDecodeError as e:
        raise DirectorError(
            f"Director returned invalid JSON: {e}",
            errors=[str(e)],
            attempts=1
        )
    
    is_valid, errors = validate_presentation(presentation)
    
    if is_valid:
        log("[Director] First attempt passed validation")
        presentation["spec_version"] = "v1.3"
        return presentation
    
    log(f"[Director] First attempt failed validation with {len(errors)} errors")
    log("[Director] Entering retry mode...")
    
    retry_system = load_prompt("director_retry_system")
    retry_user_template = load_prompt("director_retry_user")
    
    current_presentation = presentation
    current_errors = errors
    
    for attempt in range(2, MAX_RETRIES + 2):
        log(f"[Director] Retry attempt {attempt - 1} of {MAX_RETRIES}...")
        
        error_text = format_errors_for_retry(current_errors)
        failed_json = json.dumps(current_presentation, indent=2)
        
        retry_user = retry_user_template.replace("{schema_errors}", error_text)
        retry_user = retry_user.replace("{failed_json}", failed_json)
        
        response_text, usage = call_director_llm(
            system_prompt=retry_system,
            user_prompt=retry_user,
            tracker=tracker,
            phase_name=f"director_retry_{attempt - 1}"
        )
        
        if job_id:
            save_raw_llm_response(
                renderer_type="director",
                section_id=f"retry_{attempt - 1}",
                raw_response=response_text,
                model=DIRECTOR_MODEL,
                usage=usage
            )
        
        try:
            current_presentation = parse_json_response(response_text)
        except json.JSONDecodeError as e:
            log(f"[Director] Retry {attempt - 1} returned invalid JSON")
            current_errors = [f"JSON parse error: {e}"]
            continue
        
        is_valid, current_errors = validate_presentation(current_presentation)
        
        if is_valid:
            log(f"[Director] Retry {attempt - 1} passed validation")
            current_presentation["spec_version"] = "v1.3"
            return current_presentation
        
        log(f"[Director] Retry {attempt - 1} still has {len(current_errors)} errors")
    
    log("[Director] HARD FAIL - All retry attempts exhausted")
    log("[Director] This is a content issue, not a logic issue")
    
    raise DirectorError(
        f"Director failed schema validation after {MAX_RETRIES + 1} attempts. No fallbacks allowed.",
        errors=current_errors,
        attempts=MAX_RETRIES + 1
    )


def test_director(chunks_path: str, subject: str = "Physics", grade: str = "9"):
    """Test the Director with a chunks JSON file."""
    log(f"\n{'='*60}")
    log("Testing Director Client v1.3")
    log(f"{'='*60}")
    
    with open(chunks_path, "r") as f:
        chunks = json.load(f)
    
    tracker = create_tracker("test")
    
    try:
        presentation = run_director(
            chunks=chunks,
            subject=subject,
            grade=grade,
            chapter="Test Chapter",
            tracker=tracker,
            job_id="test"
        )
        
        output_path = Path(chunks_path).with_suffix(".presentation.json")
        with open(output_path, "w") as f:
            json.dump(presentation, f, indent=2)
        log(f"\nPresentation saved to: {output_path}")
        
        return presentation
        
    except DirectorError as e:
        log(f"\nFAILED: {e}")
        log(f"Errors: {e.errors[:5]}")
        return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_director(sys.argv[1])
    else:
        print("Usage: python director_client.py <chunks.json>")
