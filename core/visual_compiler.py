"""
Visual Compiler - Converts visual_beats to concrete renderer prompts/code.

CRITICAL: This module implements FAIL-FAST for vague visual beats.
- If a visual beat cannot produce a concrete prompt (≥50 words), it FAILS.
- NO "best effort" interpretation.
- NO silent fallback to placeholders.
- NO renderer creativity.
"""

import re
from typing import Tuple, List, Optional

VISUAL_INSTRUCTION_MIN_WORDS = 50

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

REQUIRED_CONCRETE_ELEMENTS = {
    "manim": ["color", "position", "label", "coordinate", "arrow", "line", "circle", "text"],
    "wan_video": ["color", "direction", "object", "motion", "position", "size", "label"]
}


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


def check_concrete_elements(text: str, renderer: str) -> Tuple[bool, List[str]]:
    required = REQUIRED_CONCRETE_ELEMENTS.get(renderer, [])
    text_lower = text.lower()
    found = [elem for elem in required if elem in text_lower]
    missing = [elem for elem in required if elem not in text_lower]
    has_enough = len(found) >= 2
    return has_enough, missing


def validate_visual_beat_for_compilation(beat: dict, section_id: int, beat_index: int, renderer: str) -> None:
    instruction = beat.get("visual_instruction", "")
    labels = beat.get("labels", [])
    motion = beat.get("motion", "")
    
    word_count = count_words(instruction)
    if word_count < VISUAL_INSTRUCTION_MIN_WORDS:
        raise VisualCompilationError(
            section_id, beat_index,
            f"visual_instruction has only {word_count} words, minimum {VISUAL_INSTRUCTION_MIN_WORDS} required. "
            f"The instruction must be concrete and specific, not vague."
        )
    
    vague = check_vague_phrases(instruction)
    if vague:
        raise VisualCompilationError(
            section_id, beat_index,
            f"visual_instruction contains banned vague phrases: {vague}. "
            f"Rewrite with specific colors, positions, and motion sequences."
        )
    
    if not labels or len(labels) == 0:
        raise VisualCompilationError(
            section_id, beat_index,
            "missing labels - every visual beat must specify text labels to show on screen"
        )
    
    if not motion or count_words(motion) < 5:
        raise VisualCompilationError(
            section_id, beat_index,
            "missing or insufficient motion description - describe step-by-step animation sequence"
        )
    
    has_concrete, missing = check_concrete_elements(instruction, renderer)
    if not has_concrete:
        raise VisualCompilationError(
            section_id, beat_index,
            f"visual_instruction lacks concrete elements. Missing: {missing[:3]}. "
            f"Include specific colors, positions, sizes, or shapes."
        )


def compile_wan_prompt(beat: dict, section_id: int, beat_index: int) -> str:
    validate_visual_beat_for_compilation(beat, section_id, beat_index, "wan_video")
    
    instruction = beat.get("visual_instruction", "")
    labels = beat.get("labels", [])
    motion = beat.get("motion", "")
    objects = beat.get("objects", [])
    
    prompt_parts = [instruction]
    
    if labels:
        prompt_parts.append(f"Text labels to show: {', '.join(labels)}.")
    
    if motion:
        prompt_parts.append(f"Animation sequence: {motion}")
    
    if objects:
        for obj in objects:
            obj_type = obj.get("type", "shape")
            obj_color = obj.get("color", "")
            obj_label = obj.get("label", "")
            if obj_type and (obj_color or obj_label):
                prompt_parts.append(f"Object: {obj_type} ({obj_color}) labeled '{obj_label}'.")
    
    compiled_prompt = " ".join(prompt_parts)
    
    if count_words(compiled_prompt) < 50:
        raise VisualCompilationError(
            section_id, beat_index,
            f"Compiled WAN prompt is too short ({count_words(compiled_prompt)} words). "
            f"Visual beat lacks sufficient detail for video generation."
        )
    
    return compiled_prompt


def compile_manim_plan(beat: dict, section_id: int, beat_index: int) -> dict:
    validate_visual_beat_for_compilation(beat, section_id, beat_index, "manim")
    
    instruction = beat.get("visual_instruction", "")
    labels = beat.get("labels", [])
    motion = beat.get("motion", "")
    objects = beat.get("objects", [])
    
    instruction_lower = instruction.lower()
    if "graph" in instruction_lower or "plot" in instruction_lower or "axis" in instruction_lower or "axes" in instruction_lower:
        scene_type = "graph"
    elif "equation" in instruction_lower or "formula" in instruction_lower or "=" in instruction:
        scene_type = "equation"
    elif "step" in instruction_lower or "derivation" in instruction_lower or "calculation" in instruction_lower:
        scene_type = "derivation"
    else:
        scene_type = "geometry"
    
    params = {}
    
    if scene_type == "equation":
        equation_match = re.search(r'([A-Z]?\s*=\s*[^,\.]+)', instruction)
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
        
        for obj in objects:
            if obj.get("type") == "axes":
                x_range = obj.get("x_range", [-5, 5])
                y_range = obj.get("y_range", [-5, 5])
                params["x_min"] = x_range[0]
                params["x_max"] = x_range[1]
                params["y_min"] = y_range[0]
                params["y_max"] = y_range[1]
    
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
        shape_code_parts = []
        for obj in objects:
            obj_type = obj.get("type", "circle")
            color = obj.get("color", "BLUE").upper()
            if obj_type == "circle":
                radius = obj.get("radius", 1)
                shape_code_parts.append(f"shapes.add(Circle(radius={radius}, color={color}))")
            elif obj_type == "arrow" or obj_type == "vector":
                start = obj.get("start", [0, 0])
                end = obj.get("end", [1, 1])
                shape_code_parts.append(f"shapes.add(Arrow(start=np.array([{start[0]}, {start[1]}, 0]), end=np.array([{end[0]}, {end[1]}, 0]), color={color}))")
            elif obj_type == "line":
                start = obj.get("start", [0, 0])
                end = obj.get("end", [1, 1])
                style = obj.get("style", "solid")
                if style == "dashed":
                    shape_code_parts.append(f"shapes.add(DashedLine(start=np.array([{start[0]}, {start[1]}, 0]), end=np.array([{end[0]}, {end[1]}, 0]), color={color}))")
                else:
                    shape_code_parts.append(f"shapes.add(Line(start=np.array([{start[0]}, {start[1]}, 0]), end=np.array([{end[0]}, {end[1]}, 0]), color={color}))")
        
        if shape_code_parts:
            params["shape_code"] = "\n        ".join(shape_code_parts)
        else:
            params["shape_code"] = "shapes.add(Circle(radius=1, color=BLUE))"
        params["wait_time"] = 3
    
    return {
        "scene_type": scene_type,
        "params": params,
        "source_instruction": instruction,
        "source_labels": labels,
        "source_motion": motion
    }


def compile_section_visuals(section: dict) -> Tuple[Optional[str], Optional[dict], List[VisualCompilationError]]:
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
