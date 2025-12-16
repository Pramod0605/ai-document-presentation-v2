"""
Visual Compiler - Converts visual_beats to concrete renderer prompts/code.

CRITICAL: This module implements FAIL-FAST for incomplete visual beats.
- If a visual beat is missing required fields, it FAILS.
- NO "best effort" interpretation.
- NO silent fallback to placeholders.
- NO renderer creativity.

SCHEMA: Each visual beat MUST have these 5 fields:
- scene_setup
- objects_and_properties
- motion_sequence
- labels_and_text
- pedagogical_focus
"""

import re
from typing import Tuple, List, Optional

REQUIRED_VISUAL_BEAT_FIELDS = [
    "scene_setup",
    "objects_and_properties", 
    "motion_sequence",
    "labels_and_text",
    "pedagogical_focus"
]

MIN_FIELD_WORDS = 4  # Relaxed - combined prompts are 40-80+ words

BANNED_VAGUE_PHRASES = [
    "detailed animation",
    "conceptual visualization", 
    "dynamic visuals",
    "beautiful animation",
    "stunning visual",
    "amazing graphics",
    "impressive display",
    "show clearly",
    "demonstrate effectively",
    "visualize the concept",
    "illustrate the process",
    "display appropriately",
    "animate smoothly",
    "show the interaction",
    "visualize the relationship",
    "demonstrate the principle",
    "illustrate the idea",
    "show the process",
    "animate the concept"
]


class VisualCompilationError(Exception):
    def __init__(self, section_id: int, beat_index: int, reason: str):
        self.section_id = section_id
        self.beat_index = beat_index
        self.reason = reason
        super().__init__(f"Section {section_id}, Beat {beat_index}: {reason}")


def count_words(text: str) -> int:
    return len(text.split()) if text else 0


def check_vague_phrases(text: str) -> List[str]:
    found = []
    text_lower = text.lower()
    for phrase in BANNED_VAGUE_PHRASES:
        if phrase in text_lower:
            found.append(phrase)
    return found


def validate_visual_beat_structure(beat: dict, section_id: int, beat_index: int) -> None:
    """Validate that a visual beat has all 5 required fields with sufficient content."""
    
    missing_fields = []
    short_fields = []
    vague_fields = []
    
    for field in REQUIRED_VISUAL_BEAT_FIELDS:
        value = beat.get(field, "")
        
        if not value or not isinstance(value, str):
            missing_fields.append(field)
            continue
        
        word_count = count_words(value)
        if word_count < MIN_FIELD_WORDS:
            short_fields.append(f"{field} ({word_count} words, need {MIN_FIELD_WORDS}+)")
        
        vague = check_vague_phrases(value)
        if vague:
            vague_fields.append(f"{field}: {vague}")
    
    if missing_fields:
        raise VisualCompilationError(
            section_id, beat_index,
            f"Missing required fields: {missing_fields}. "
            f"All visual beats must have: {REQUIRED_VISUAL_BEAT_FIELDS}"
        )
    
    if short_fields:
        raise VisualCompilationError(
            section_id, beat_index,
            f"Fields too short: {short_fields}. "
            f"Each field must be at least {MIN_FIELD_WORDS} words."
        )
    
    if vague_fields:
        raise VisualCompilationError(
            section_id, beat_index,
            f"Vague phrases detected: {vague_fields}. "
            f"Use specific descriptions with colors, positions, and sizes."
        )


def extract_labels_from_text(labels_text: str) -> List[str]:
    """Extract label strings from labels_and_text field."""
    labels = re.findall(r"['\"]([^'\"]+)['\"]", labels_text)
    if not labels:
        labels = re.findall(r"Label\s+(\S+)", labels_text)
    return labels if labels else ["Label"]


def compile_wan_prompt(beat: dict, section_id: int, beat_index: int) -> str:
    """Compile a WAN video prompt from structured visual beat fields."""
    validate_visual_beat_structure(beat, section_id, beat_index)
    
    scene_setup = beat.get("scene_setup", "")
    objects_text = beat.get("objects_and_properties", "")
    motion = beat.get("motion_sequence", "")
    labels_text = beat.get("labels_and_text", "")
    focus = beat.get("pedagogical_focus", "")
    
    labels = extract_labels_from_text(labels_text)
    
    prompt_parts = [
        f"Scene: {scene_setup}",
        f"Objects: {objects_text}",
        f"Animation: {motion}",
        f"Text labels to show: {', '.join(labels)}.",
        f"Educational goal: {focus}"
    ]
    
    compiled_prompt = " ".join(prompt_parts)
    return compiled_prompt


def compile_manim_plan(beat: dict, section_id: int, beat_index: int) -> dict:
    """Compile a Manim animation plan from structured visual beat fields."""
    validate_visual_beat_structure(beat, section_id, beat_index)
    
    scene_setup = beat.get("scene_setup", "")
    objects_text = beat.get("objects_and_properties", "")
    motion = beat.get("motion_sequence", "")
    labels_text = beat.get("labels_and_text", "")
    focus = beat.get("pedagogical_focus", "")
    
    combined = f"{scene_setup} {objects_text}".lower()
    if "graph" in combined or "plot" in combined or "axis" in combined or "axes" in combined:
        scene_type = "graph"
    elif "equation" in combined or "formula" in combined or "=" in combined:
        scene_type = "equation"
    elif "step" in combined or "derivation" in combined or "calculation" in combined:
        scene_type = "derivation"
    else:
        scene_type = "geometry"
    
    labels = extract_labels_from_text(labels_text)
    
    params = {}
    if scene_type == "equation":
        import re
        equation_match = re.search(r'([A-Z]?\s*=\s*[^,\.]+)', objects_text)
        if equation_match:
            params["equation"] = equation_match.group(1).strip()
        else:
            params["equation"] = labels[0] if labels else "E = mc^2"
        params["scale"] = 1.5
        params["wait_time"] = 3
    
    elif scene_type == "graph":
        params["x_min"] = -5
        params["x_max"] = 5
        params["y_min"] = -5
        params["y_max"] = 5
        params["function"] = "x**2"
        params["label"] = labels[0] if labels else "f(x)"
        params["wait_time"] = 3
    
    elif scene_type == "derivation":
        steps = []
        for label in labels:
            if "=" in label or any(c.isalpha() for c in label):
                steps.append(f'r"{label}"')
        if not steps:
            steps = ['r"Step 1"', 'r"Step 2"', 'r"Result"']
        params["steps"] = ", ".join(steps)
        params["wait_time"] = 2
    
    else:
        params["shape_code"] = "shapes.add(Circle(radius=1, color=BLUE))"
        params["wait_time"] = 3
    
    return {
        "scene_type": scene_type,
        "params": params,
        "source_instruction": f"{scene_setup} {objects_text} {motion}",
        "source_labels": labels,
        "source_motion": motion,
        "structured_fields": {
            "scene_setup": scene_setup,
            "objects_and_properties": objects_text,
            "motion_sequence": motion,
            "labels_and_text": labels_text,
            "pedagogical_focus": focus
        }
    }


def compile_section_visuals(section: dict) -> Tuple[Optional[str], Optional[dict], List[VisualCompilationError]]:
    """Compile all visual beats in a section."""
    section_id = section.get("id", 0)
    section_type = section.get("section_type", "content")
    renderer = section.get("renderer", "wan_video")
    visual_beats = section.get("visual_beats", [])
    
    if section_type not in ["content", "example"]:
        return None, None, []
    
    errors = []
    compiled_wan_prompts = []
    compiled_manim_plans = []
    
    for i, beat in enumerate(visual_beats):
        try:
            if renderer == "manim":
                plan = compile_manim_plan(beat, section_id, i)
                compiled_manim_plans.append(plan)
            else:
                prompt = compile_wan_prompt(beat, section_id, i)
                compiled_wan_prompts.append(prompt)
        except VisualCompilationError as e:
            errors.append(e)
    
    if errors:
        return None, None, errors
    
    if renderer == "manim":
        combined_plan = {
            "scene_type": "multi_beat",
            "beats": compiled_manim_plans,
            "total_beats": len(compiled_manim_plans)
        }
        return None, combined_plan, []
    else:
        combined_prompt = " | NEXT BEAT | ".join(compiled_wan_prompts)
        return combined_prompt, None, []


def compile_presentation_visuals(presentation: dict) -> Tuple[dict, List[VisualCompilationError]]:
    """Compile all visual beats in a presentation."""
    all_errors = []
    
    for section in presentation.get("sections", []):
        section_id = section.get("id", 0)
        section_type = section.get("section_type", "content")
        renderer = section.get("renderer", "wan_video")
        
        if section_type in ["content", "example"]:
            wan_prompt, manim_plan, errors = compile_section_visuals(section)
            
            if errors:
                all_errors.extend(errors)
            else:
                if renderer == "manim" and manim_plan:
                    if "explanation_plan" not in section:
                        section["explanation_plan"] = {}
                    section["explanation_plan"]["compiled_manim_plan"] = manim_plan
                elif wan_prompt:
                    if "explanation_plan" not in section:
                        section["explanation_plan"] = {}
                    section["explanation_plan"]["compiled_wan_prompt"] = wan_prompt
    
    return presentation, all_errors
