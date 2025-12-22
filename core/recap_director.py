"""
Recap Director v1.4 - Pass 1b: Memory & Recap Generation

Generates:
- Memory section: 5 flashcards with R-A-S mnemonic style
- Recap section: 5 scenes with video prompts (300+ words each)

Receives FULL markdown for complete context (not chunked).
Uses Gemini 2.5 Pro with structured output.
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

MODEL = "google/gemini-2.5-pro"

MAX_STRUCTURAL_RETRIES = 2
MAX_SEMANTIC_RETRIES = 1

MIN_VIDEO_PROMPT_WORDS = 300
REQUIRED_FLASHCARD_COUNT = 5
REQUIRED_SCENE_COUNT = 5
MIN_RECAP_NARRATION_WORDS = 300
MAX_RECAP_NARRATION_WORDS = 500


def load_prompt(name: str) -> str:
    """Load a prompt file."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, "r") as f:
        return f.read()


def call_recap_director(
    full_markdown: str,
    subject: str,
    grade: str,
    tracker: Optional[AnalyticsTracker] = None,
    max_structural_retries: int = MAX_STRUCTURAL_RETRIES,
    max_semantic_retries: int = MAX_SEMANTIC_RETRIES
) -> Dict:
    """
    PASS 1b: Generate memory and recap sections.
    
    Memory section:
    - Exactly 5 flashcards with mnemonic letters
    - Renderer: remotion
    
    Recap section:
    - Exactly 5 scenes with video prompts (300+ words each)
    - Total narration: 300-500 words
    - Renderer: video (WAN)
    - Avatar: MUST be hidden
    
    Args:
        full_markdown: Complete markdown content (not chunked)
        subject: Subject area
        grade: Grade level
        tracker: Analytics tracker
        max_structural_retries: Max retries for structural errors (default 2)
        max_semantic_retries: Max retries for semantic errors (default 1)
        
    Returns:
        Dict with sections array containing memory and recap
        
    Raises:
        RecapDirectorError: If generation fails after all retries
    """
    logger.info(f"[Recap Director] Starting memory/recap for {subject} {grade}")
    
    system_prompt = load_prompt("recap_director_system_v1.4")
    user_prompt_template = load_prompt("recap_director_user_v1.4")
    
    user_prompt = user_prompt_template.format(
        subject=subject,
        grade=grade,
        full_markdown=full_markdown
    )
    
    structural_attempts = 0
    semantic_attempts = 0
    last_error = None
    
    while True:
        try:
            if tracker:
                tracker.start_phase("recap_director", MODEL)
            
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=16000,
                response_format={"type": "json_object"}
            )
            
            raw_response = response.choices[0].message.content or ""
            
            if not raw_response:
                raise RecapDirectorError("Empty response from LLM")
            
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            
            if tracker:
                tracker.end_phase("recap_director", input_tokens, output_tokens)
            
            result = repair_and_parse_json(raw_response)
            
            structural_errors = _validate_structure(result)
            if structural_errors:
                structural_attempts += 1
                if structural_attempts > max_structural_retries:
                    raise StructuralValidationError(structural_errors)
                logger.warning(f"[Recap Director] Structural retry {structural_attempts}/{max_structural_retries}")
                user_prompt = _get_structural_retry_prompt(user_prompt, structural_errors)
                continue
            
            semantic_errors = _validate_semantics(result)
            if semantic_errors:
                semantic_attempts += 1
                if semantic_attempts > max_semantic_retries:
                    raise SemanticValidationError(semantic_errors)
                logger.warning(f"[Recap Director] Semantic retry {semantic_attempts}/{max_semantic_retries}")
                user_prompt = _get_semantic_retry_prompt(user_prompt, semantic_errors)
                continue
            
            logger.info("[Recap Director] Successfully generated memory + recap sections")
            return result
            
        except (json.JSONDecodeError) as e:
            structural_attempts += 1
            last_error = e
            if structural_attempts > max_structural_retries:
                raise RecapDirectorError(f"JSON parse failed: {e}")
            logger.warning(f"[Recap Director] JSON retry {structural_attempts}/{max_structural_retries}: {e}")
            user_prompt = _get_json_repair_prompt(user_prompt, str(e))
            
        except (StructuralValidationError, SemanticValidationError) as e:
            last_error = e
            raise RecapDirectorError(f"Validation failed: {e}")
            
        except Exception as e:
            logger.error(f"[Recap Director] Unexpected error: {e}")
            raise RecapDirectorError(f"Unexpected error: {e}")


def _validate_structure(data: Dict) -> List[str]:
    """Validate structural requirements."""
    errors = []
    
    if "sections" not in data:
        errors.append("Missing 'sections' array")
        return errors
    
    sections = data.get("sections", [])
    
    if len(sections) != 2:
        errors.append(f"Must have exactly 2 sections (memory + recap), got {len(sections)}")
    
    section_types = [s.get("section_type") for s in sections]
    
    if "memory" not in section_types:
        errors.append("Missing required 'memory' section")
    if "recap" not in section_types:
        errors.append("Missing required 'recap' section")
    
    for section_type in section_types:
        if section_type not in ["memory", "recap"]:
            errors.append(f"Invalid section_type '{section_type}' - only 'memory' and 'recap' allowed")
    
    for i, section in enumerate(sections):
        section_errors = _validate_section_structure(section, i)
        errors.extend(section_errors)
    
    return errors


def _validate_section_structure(section: Dict, index: int) -> List[str]:
    """Validate structure of a single section."""
    errors = []
    prefix = f"sections[{index}]"
    section_type = section.get("section_type")
    
    required = ["section_id", "section_type", "renderer", "narration"]
    for field in required:
        if field not in section:
            errors.append(f"{prefix}: missing required field '{field}'")
    
    if section_type == "memory":
        if section.get("renderer") != "remotion":
            errors.append(f"{prefix}: memory section must use 'remotion' renderer")
        
        flashcards = section.get("flashcards", [])
        if not flashcards:
            errors.append(f"{prefix}: memory section missing 'flashcards' array")
        elif len(flashcards) != REQUIRED_FLASHCARD_COUNT:
            errors.append(f"{prefix}: memory section must have exactly {REQUIRED_FLASHCARD_COUNT} flashcards, got {len(flashcards)}")
        
        for j, card in enumerate(flashcards):
            card_required = ["mnemonic_letter", "concept", "definition"]
            for field in card_required:
                if field not in card:
                    errors.append(f"{prefix}.flashcards[{j}]: missing '{field}'")
    
    elif section_type == "recap":
        if section.get("renderer") != "video":
            errors.append(f"{prefix}: recap section must use 'video' renderer (WAN)")
        
        video_prompts = section.get("video_prompts", [])
        if not video_prompts:
            errors.append(f"{prefix}: recap section missing 'video_prompts' array")
        elif len(video_prompts) != REQUIRED_SCENE_COUNT:
            errors.append(f"{prefix}: recap section must have exactly {REQUIRED_SCENE_COUNT} video_prompts, got {len(video_prompts)}")
        
        for j, prompt in enumerate(video_prompts):
            prompt_required = ["beat_id", "prompt"]
            for field in prompt_required:
                if field not in prompt:
                    errors.append(f"{prefix}.video_prompts[{j}]: missing '{field}'")
    
    narration = section.get("narration", {})
    if not isinstance(narration, dict):
        errors.append(f"{prefix}: narration must be an object")
    elif "full_text" not in narration:
        errors.append(f"{prefix}: narration missing 'full_text'")
    
    return errors


def _validate_semantics(data: Dict) -> List[str]:
    """Validate semantic requirements."""
    errors = []
    
    sections = data.get("sections", [])
    
    for i, section in enumerate(sections):
        prefix = f"sections[{i}]"
        section_type = section.get("section_type")
        
        if section_type == "recap":
            layout = section.get("layout", {})
            avatar_pos = layout.get("avatar_position", "hidden")
            
            if avatar_pos != "hidden":
                errors.append(f"{prefix}: recap section avatar_position must be 'hidden', got '{avatar_pos}'")
            
            segments = section.get("narration", {}).get("segments", [])
            for j, seg in enumerate(segments):
                dd = seg.get("display_directives", {})
                avatar_layer = dd.get("avatar_layer")
                if avatar_layer and avatar_layer != "hide":
                    errors.append(f"{prefix}.segments[{j}]: recap avatar_layer must be 'hide', got '{avatar_layer}'")
            
            narration = section.get("narration", {})
            full_text = narration.get("full_text", "")
            word_count = len(full_text.split())
            
            if word_count < MIN_RECAP_NARRATION_WORDS:
                errors.append(f"{prefix}: recap narration too short ({word_count} words, minimum {MIN_RECAP_NARRATION_WORDS})")
            if word_count > MAX_RECAP_NARRATION_WORDS:
                errors.append(f"{prefix}: recap narration too long ({word_count} words, maximum {MAX_RECAP_NARRATION_WORDS})")
            
            video_prompts = section.get("video_prompts", [])
            for j, vp in enumerate(video_prompts):
                prompt_text = vp.get("prompt", "")
                prompt_words = len(prompt_text.split())
                if prompt_words < MIN_VIDEO_PROMPT_WORDS:
                    errors.append(f"{prefix}.video_prompts[{j}]: prompt too short ({prompt_words} words, minimum {MIN_VIDEO_PROMPT_WORDS})")
    
    return errors


def _get_structural_retry_prompt(original_prompt: str, errors: List[str]) -> str:
    """Generate retry prompt for structural errors."""
    error_list = "\n".join(f"- {e}" for e in errors)
    return original_prompt + f"""

---
STRUCTURAL ERRORS - RETRY REQUIRED:
{error_list}

Fix these issues:
1. Output EXACTLY 2 sections: one 'memory', one 'recap'
2. Memory section: must have exactly 5 flashcards with mnemonic_letter, concept, definition
3. Recap section: must have exactly 5 video_prompts with beat_id, prompt
4. Memory renderer must be 'remotion'
5. Recap renderer must be 'video'
---
"""


def _get_semantic_retry_prompt(original_prompt: str, errors: List[str]) -> str:
    """Generate retry prompt for semantic errors."""
    error_list = "\n".join(f"- {e}" for e in errors)
    return original_prompt + f"""

---
SEMANTIC ERRORS - RETRY REQUIRED:
{error_list}

Fix these content issues:
1. Recap section avatar_position must be 'hidden'
2. Recap section avatar_layer in all segments must be 'hide'
3. Recap narration must be 300-500 words total
4. Each video_prompt must be 300+ words (cinematic, detailed, NO infographics)
---
"""


def _get_json_repair_prompt(original_prompt: str, error: str) -> str:
    """Generate retry prompt for JSON parse errors."""
    return original_prompt + f"""

---
JSON PARSE ERROR - RETRY REQUIRED:
{error}

Ensure your response is valid JSON:
1. No trailing commas before }} or ]]
2. All strings properly quoted
3. No comments in JSON
4. Complete all arrays and objects
---
"""


class RecapDirectorError(Exception):
    """Error raised when Recap Director fails."""
    pass


class StructuralValidationError(Exception):
    """Error raised for structural validation failures."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Structural errors: {', '.join(errors)}")


class SemanticValidationError(Exception):
    """Error raised for semantic validation failures."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Semantic errors: {', '.join(errors)}")
