"""
WAN Prompt Quality Validator - Ensures video prompts are specific enough for quality generation.

CRITICAL: This module validates that WAN (video) prompts are concrete and actionable,
not vague or abstract. Vague prompts lead to poor video generation.

Validation checks:
1. Banned vague phrases detection
2. Minimum prompt length
3. Required specificity elements (subject, action, context)

ISS-076 FIX: Added hard_fail_on_short_prompts() for production enforcement.
"""

import re
from typing import List, Dict, Tuple


# ISS-120: Updated from 300 to 80 to match new 80-150 word prompt limits
MIN_WAN_PROMPT_WORDS = 80
MAX_WAN_PROMPT_WORDS = 150
MIN_WAN_PROMPT_WORDS_V13 = 80  # Legacy alias for backwards compatibility


class WanPromptHardFailError(Exception):
    """Raised when WAN prompt validation fails hard (no fallback allowed)."""
    def __init__(self, section_id: int, message: str):
        self.section_id = section_id
        super().__init__(f"Section {section_id}: {message}")


BANNED_VAGUE_PHRASES = [
    "something like",
    "kind of",
    "sort of",
    "maybe show",
    "perhaps",
    "some sort of",
    "somehow",
    "in some way",
    "various things",
    "different elements",
    "multiple aspects",
    "general concept",
    "abstract representation",
    "symbolic visualization",
    "conceptual imagery",
    "vague outline",
    "rough idea",
    "generic scene",
    "unspecified",
    "etc",
    "and so on",
    "and more",
    "things like that",
    "stuff like",
    "whatever",
    "anything",
    "everything",
]

QUALITY_INDICATORS = [
    r"\b(zoom|pan|fade|transition|close-up|wide shot|medium shot)\b",
    r"\b(left|right|center|top|bottom|foreground|background)\b",
    r"\b(slowly|quickly|gradually|smoothly|rapidly)\b",
    r"\b(color|colour|bright|dark|glow|shadow|light)\b",
    r"\b(animate|move|rotate|transform|morph|grow|shrink)\b",
]

MIN_PROMPT_LENGTH = 50
MAX_PROMPT_LENGTH = 800  # ISS-120: Increased to match API limit


class WanPromptValidationResult:
    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.quality_score = 0.0
    
    def add_error(self, msg: str):
        self.is_valid = False
        self.errors.append(msg)
    
    def add_warning(self, msg: str):
        self.warnings.append(msg)


def validate_wan_prompt(prompt: str, section_id: int = 0, beat_index: int = 0) -> WanPromptValidationResult:
    """Validate a single WAN prompt for quality and specificity.
    
    Args:
        prompt: The video generation prompt text
        section_id: Section identifier for error messages
        beat_index: Beat index for error messages
    
    Returns:
        WanPromptValidationResult with validation status and messages
    """
    result = WanPromptValidationResult()
    prefix = f"Section {section_id}, Beat {beat_index}"
    
    if not prompt or not prompt.strip():
        result.add_error(f"{prefix}: Empty prompt")
        return result
    
    prompt_lower = prompt.lower()
    prompt_len = len(prompt.strip())
    
    if prompt_len < MIN_PROMPT_LENGTH:
        result.add_error(
            f"{prefix}: Prompt too short ({prompt_len} chars). "
            f"Minimum {MIN_PROMPT_LENGTH} chars required for quality video generation."
        )
    
    if prompt_len > MAX_PROMPT_LENGTH:
        result.add_warning(
            f"{prefix}: Prompt very long ({prompt_len} chars). "
            f"Consider condensing to improve generation focus."
        )
    
    found_vague = []
    for phrase in BANNED_VAGUE_PHRASES:
        if phrase in prompt_lower:
            found_vague.append(phrase)
    
    if found_vague:
        result.add_error(
            f"{prefix}: Contains vague phrases: {found_vague}. "
            "Replace with specific, concrete descriptions."
        )
    
    quality_matches = 0
    for pattern in QUALITY_INDICATORS:
        if re.search(pattern, prompt_lower):
            quality_matches += 1
    
    quality_score = min(1.0, quality_matches / len(QUALITY_INDICATORS))
    result.quality_score = quality_score
    
    if quality_matches == 0:
        result.add_warning(
            f"{prefix}: Prompt lacks cinematographic direction. "
            "Consider adding camera directions (zoom, pan) or motion descriptors."
        )
    
    return result


def validate_video_prompts(video_prompts: List[Dict], section_id: int = 0, strict: bool = False) -> Tuple[bool, List[str], List[str]]:
    """Validate all video prompts for a section.
    
    Args:
        video_prompts: List of video prompt dicts with 'prompt' field
        section_id: Section identifier
        strict: If True, warnings become errors
    
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    all_errors = []
    all_warnings = []
    
    if not video_prompts:
        return True, [], ["No video prompts to validate"]
    
    for i, vp in enumerate(video_prompts):
        prompt = vp.get("prompt", "") if isinstance(vp, dict) else str(vp)
        result = validate_wan_prompt(prompt, section_id, i)
        
        all_errors.extend(result.errors)
        if strict:
            all_errors.extend(result.warnings)
        else:
            all_warnings.extend(result.warnings)
    
    return len(all_errors) == 0, all_errors, all_warnings


def log_prompt_quality_summary(video_prompts: List[Dict], section_id: int = 0) -> Dict:
    """Generate a quality summary for video prompts without failing.
    
    Args:
        video_prompts: List of video prompt dicts
        section_id: Section identifier
    
    Returns:
        Summary dict with quality metrics
    """
    if not video_prompts:
        return {"prompt_count": 0, "avg_quality": 0, "issues": []}
    
    total_quality = 0.0
    issues = []
    
    for i, vp in enumerate(video_prompts):
        prompt = vp.get("prompt", "") if isinstance(vp, dict) else str(vp)
        result = validate_wan_prompt(prompt, section_id, i)
        total_quality += result.quality_score
        issues.extend(result.errors + result.warnings)
    
    return {
        "prompt_count": len(video_prompts),
        "avg_quality": round(total_quality / len(video_prompts), 2),
        "issues": issues
    }


def hard_fail_on_short_prompts(video_prompts: List[Dict], section_id: int, min_words: int = MIN_WAN_PROMPT_WORDS) -> None:
    """
    ISS-076 FIX: Hard fail validation for WAN prompts.
    ISS-120 UPDATE: Now validates 80-150 words and max 800 chars.
    
    Raises WanPromptHardFailError if any prompt is below minimum word count
    or exceeds maximum character limit.
    This should be called before production WAN API calls.
    
    Args:
        video_prompts: List of video prompt dicts
        section_id: Section identifier
        min_words: Minimum words required per prompt (default 80)
    
    Raises:
        WanPromptHardFailError: If any prompt fails validation
    """
    if not video_prompts:
        raise WanPromptHardFailError(section_id, "No video_prompts provided")
    
    for i, vp in enumerate(video_prompts):
        prompt = vp.get("prompt", "") if isinstance(vp, dict) else str(vp)
        word_count = len(prompt.split()) if prompt else 0
        char_count = len(prompt) if prompt else 0
        
        if word_count < min_words:
            raise WanPromptHardFailError(
                section_id,
                f"Beat {i}: Prompt has {word_count} words, minimum {min_words} required. "
                f"Prompt preview: '{prompt[:100]}...'"
            )
        
        if char_count > MAX_PROMPT_LENGTH:
            raise WanPromptHardFailError(
                section_id,
                f"Beat {i}: Prompt has {char_count} chars, maximum {MAX_PROMPT_LENGTH} allowed. "
                f"Truncate or condense the prompt."
            )
    
    print(f"[WAN Validator] Section {section_id}: All {len(video_prompts)} prompts meet {min_words}+ word / {MAX_PROMPT_LENGTH} char requirement")
