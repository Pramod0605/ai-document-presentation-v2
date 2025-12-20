"""
Hard Fail Validator - Implements hard fail conditions for v1.1 and v1.2.

These conditions MUST cause generation to fail - no fallbacks allowed.
Reference: docs/llm_output_requirements.json validation_rules.hard_fail_conditions

Hard Fail Conditions:
1. content_or_example_narration_below_minimum
2. missing_visual_beats
3. example_without_step_visualization
4. formula_mentioned_but_not_visualized
5. vague_visual_language_detected
6. manim_section_without_scene_spec (v1.2: checks section-level spec)
7. remotion_section_without_scene_spec (v1.2 NEW)
8. video_section_without_prompts (v1.2 NEW)
"""

import re
from typing import List, Tuple, Dict, Any

CONTENT_MIN_WORDS = 150
EXAMPLE_MIN_WORDS = 100
EXAMPLE_REQUIRED_STEPS = 5

VAGUE_PHRASES = [
    "appropriate animation", "suitable visual", "relevant content",
    "necessary elements", "various objects", "etc", "and so on",
    "properly animated", "correctly displayed", "accordingly",
    "as needed", "as required", "generic visual", "typical animation",
    "standard display", "some kind of", "some sort of", "a type of",
    "appropriate visual", "suitable animation", "relevant visual"
]

FORMULA_PATTERNS = [
    r'F\s*=\s*m\s*[*×·]\s*a',
    r'E\s*=\s*m\s*c\s*²',
    r'v\s*=\s*u\s*[+\-]\s*a\s*t',
    r's\s*=\s*ut\s*[+\-]',
    r'[A-Z]\s*=\s*[A-Z0-9\s\+\-\*/\^]{3,}',
    r'\\frac\{',
    r'\\sum',
    r'\\int',
    r'\bformula\b',
    r'\bequation\b',
    r'\bcalculate the\b',
    r'\bcompute the\b',
    r'\bderivation\b',
]


class HardFailError(Exception):
    """Raised when a hard fail condition is detected. NO FALLBACK ALLOWED."""
    def __init__(self, condition: str, section_id: int, details: str):
        self.condition = condition
        self.section_id = section_id
        self.details = details
        super().__init__(f"HARD FAIL [{condition}] Section {section_id}: {details}")


def count_words(text: str) -> int:
    """Count words in text."""
    if not text:
        return 0
    return len(text.split())


def check_vague_phrases(text: str) -> List[str]:
    """Return list of vague phrases found in text."""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for phrase in VAGUE_PHRASES:
        if phrase.lower() in text_lower:
            found.append(phrase)
    return found


def check_formula_in_narration(narration: str) -> bool:
    """Check if narration mentions formulas/equations."""
    if not narration:
        return False
    for pattern in FORMULA_PATTERNS:
        if re.search(pattern, narration, re.IGNORECASE):
            return True
    return False


def validate_hard_fail_conditions(section: dict) -> List[HardFailError]:
    """
    Validate all 6 hard fail conditions for a section.
    
    Returns list of HardFailError instances (empty if valid).
    """
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "unknown")
    renderer = section.get("renderer", "")
    narration = section.get("narration", "")
    word_count = count_words(narration)
    visual_beats = section.get("visual_beats", [])
    narration_segments = section.get("narration_segments", [])
    
    embedded_visual_beats = [
        seg.get("visual_beat") for seg in narration_segments 
        if seg.get("visual_beat")
    ]
    
    effective_visual_beats = visual_beats if visual_beats else embedded_visual_beats
    
    if section_type == "content":
        if word_count < CONTENT_MIN_WORDS:
            errors.append(HardFailError(
                "content_or_example_narration_below_minimum",
                section_id,
                f"Content section has {word_count} words, minimum is {CONTENT_MIN_WORDS}"
            ))
        
        if narration_segments and not effective_visual_beats:
            errors.append(HardFailError(
                "missing_visual_beats",
                section_id,
                f"Content section has {len(narration_segments)} narration segments but no visual beats"
            ))
    
    if section_type == "example":
        if word_count < EXAMPLE_MIN_WORDS:
            errors.append(HardFailError(
                "content_or_example_narration_below_minimum",
                section_id,
                f"Example section has {word_count} words, minimum is {EXAMPLE_MIN_WORDS}"
            ))
        
        if not effective_visual_beats:
            errors.append(HardFailError(
                "example_without_step_visualization",
                section_id,
                "Example section has no visual beats - examples must be visualized step-by-step"
            ))
        elif len(effective_visual_beats) < EXAMPLE_REQUIRED_STEPS:
            errors.append(HardFailError(
                "example_without_step_visualization",
                section_id,
                f"Example section has {len(effective_visual_beats)} visual beats, need {EXAMPLE_REQUIRED_STEPS} for 5-step structure"
            ))
    
    if section_type in ["content", "example"] and check_formula_in_narration(narration):
        has_formula_visual = False
        
        section_manim_spec = section.get("manim_scene_spec", {})
        if section_manim_spec:
            objects = section_manim_spec.get("objects", [])
            for obj in objects:
                if obj.get("type") == "equation" or obj.get("properties", {}).get("latex"):
                    has_formula_visual = True
                    break
        
        if not has_formula_visual:
            for beat in effective_visual_beats:
                if not isinstance(beat, dict):
                    continue
                labels = beat.get("labels_and_text", "") or beat.get("description", "")
                manim_spec = beat.get("manim_scene_spec", {})
                equations = manim_spec.get("equations", []) if manim_spec else []
                
                if equations or re.search(r'[a-zA-Z]\s*=', labels):
                    has_formula_visual = True
                    break
        
        if not has_formula_visual:
            errors.append(HardFailError(
                "formula_mentioned_but_not_visualized",
                section_id,
                "Narration mentions formulas/equations but no visual beat shows them"
            ))
    
    if section_type in ["content", "example"]:
        for i, beat in enumerate(effective_visual_beats):
            if not isinstance(beat, dict):
                continue
            fields_to_check = ["scene_setup", "objects_and_properties", "motion_sequence", "labels_and_text", "description"]
            for field in fields_to_check:
                value = beat.get(field, "")
                if value:
                    vague = check_vague_phrases(value)
                    if vague:
                        errors.append(HardFailError(
                            "vague_visual_language_detected",
                            section_id,
                            f"Visual beat {i} field '{field}' contains vague phrases: {vague}"
                        ))
                        break
    
    if renderer == "manim" and section_type in ["content", "example"]:
        section_manim_spec = section.get("manim_scene_spec")
        
        if section_manim_spec:
            objects = section_manim_spec.get("objects", [])
            equations = section_manim_spec.get("equations", [])
            forces = section_manim_spec.get("forces", [])
            animation_seq = section_manim_spec.get("animation_sequence", [])
            
            if not objects and not equations and not forces:
                errors.append(HardFailError(
                    "manim_section_without_scene_spec",
                    section_id,
                    "Section manim_scene_spec has no renderable content (objects/equations/forces)"
                ))
            if not animation_seq:
                errors.append(HardFailError(
                    "manim_section_without_scene_spec",
                    section_id,
                    "Section manim_scene_spec has no animation_sequence"
                ))
        else:
            has_beat_level_spec = any(beat.get("manim_scene_spec") for beat in visual_beats if isinstance(beat, dict))
            if not has_beat_level_spec:
                errors.append(HardFailError(
                    "manim_section_without_scene_spec",
                    section_id,
                    "Manim section has no manim_scene_spec (neither section-level nor beat-level)"
                ))
    
    if renderer == "remotion" and section_type in ["content", "example"]:
        if not section.get("remotion_scene_spec"):
            errors.append(HardFailError(
                "remotion_section_without_scene_spec",
                section_id,
                "Remotion section has no remotion_scene_spec"
            ))
    
    if renderer in ["video", "wan", "wan_video"] and section_type in ["content", "example"]:
        if not section.get("video_prompts") and not section.get("recap_scenes"):
            errors.append(HardFailError(
                "video_section_without_prompts",
                section_id,
                "Video section has no video_prompts"
            ))
    
    return errors


def validate_presentation_hard_fails(presentation: dict) -> Tuple[bool, List[HardFailError]]:
    """
    Validate entire presentation against all hard fail conditions.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    all_errors = []
    sections = presentation.get("sections", [])
    
    for section in sections:
        section_errors = validate_hard_fail_conditions(section)
        all_errors.extend(section_errors)
    
    return len(all_errors) == 0, all_errors


def format_hard_fail_report(errors: List[HardFailError]) -> str:
    """Format hard fail errors into a readable report."""
    if not errors:
        return "No hard fail conditions detected."
    
    lines = [
        "=" * 60,
        "HARD FAIL VALIDATION REPORT",
        "=" * 60,
        f"Total failures: {len(errors)}",
        ""
    ]
    
    by_condition = {}
    for err in errors:
        if err.condition not in by_condition:
            by_condition[err.condition] = []
        by_condition[err.condition].append(err)
    
    for condition, errs in by_condition.items():
        lines.append(f"\n[{condition}] - {len(errs)} occurrence(s)")
        for err in errs:
            lines.append(f"  Section {err.section_id}: {err.details}")
    
    lines.append("\n" + "=" * 60)
    return "\n".join(lines)
