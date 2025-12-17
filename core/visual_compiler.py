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


COLOR_MAP = {
    "blue": "BLUE",
    "red": "RED",
    "green": "GREEN",
    "orange": "ORANGE",
    "yellow": "YELLOW",
    "purple": "PURPLE",
    "white": "WHITE",
    "gray": "GRAY",
    "grey": "GRAY",
    "pink": "PINK",
    "cyan": "TEAL",
}

POSITION_MAP = {
    "top_center": "UP * 3",
    "top_left": "UP * 3 + LEFT * 4",
    "top_right": "UP * 3 + RIGHT * 4",
    "bottom_center": "DOWN * 3",
    "bottom_left": "DOWN * 3 + LEFT * 4",
    "bottom_right": "DOWN * 3 + RIGHT * 4",
    "left": "LEFT * 5",
    "right": "RIGHT * 5",
    "center": "ORIGIN",
}


def validate_manim_scene_spec(spec: dict, section_id: int, beat_index: int) -> None:
    """Validate manim_scene_spec has required structure."""
    if not spec:
        raise VisualCompilationError(
            section_id, beat_index,
            "Missing manim_scene_spec. Manim sections require structured scene specs, not prose descriptions."
        )
    
    objects = spec.get("objects", [])
    if not objects:
        raise VisualCompilationError(
            section_id, beat_index,
            "manim_scene_spec.objects is empty. Must define at least one object (charge, vector, equation)."
        )
    
    animation_sequence = spec.get("animation_sequence", [])
    if not animation_sequence:
        raise VisualCompilationError(
            section_id, beat_index,
            "manim_scene_spec.animation_sequence is empty. Must define animation actions."
        )
    
    for obj in objects:
        if not obj.get("id"):
            raise VisualCompilationError(
                section_id, beat_index,
                f"Object missing 'id' field: {obj}"
            )
        if not obj.get("type"):
            raise VisualCompilationError(
                section_id, beat_index,
                f"Object '{obj.get('id')}' missing 'type' field"
            )


def translate_spec_to_manim_code(spec: dict, section_id: int, beat_index: int) -> str:
    """Translate manim_scene_spec to executable Manim code."""
    validate_manim_scene_spec(spec, section_id, beat_index)
    
    code_lines = []
    object_vars = {}
    
    objects = spec.get("objects", [])
    for obj in objects:
        obj_id = obj["id"]
        obj_type = obj["type"]
        position = obj.get("position", [0, 0])
        props = obj.get("properties", {})
        
        color = COLOR_MAP.get(props.get("color", "blue").lower(), "BLUE")
        label_text = props.get("label", "")
        radius = props.get("radius", 0.3)
        
        var_name = obj_id.replace("-", "_").replace(" ", "_")
        object_vars[obj_id] = var_name
        
        if obj_type == "point_charge":
            code_lines.append(f'{var_name} = Dot(point=np.array([{position[0]}, {position[1]}, 0]), color={color}, radius={radius})')
            if label_text:
                code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=24).next_to({var_name}, UP)')
        
        elif obj_type == "charged_sphere":
            code_lines.append(f'{var_name} = Circle(radius={radius}, color={color}, fill_opacity=0.5).move_to(np.array([{position[0]}, {position[1]}, 0]))')
            if label_text:
                code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=24).next_to({var_name}, UP)')
        
        elif obj_type == "point":
            code_lines.append(f'{var_name} = Dot(point=np.array([{position[0]}, {position[1]}, 0]), color={color})')
            if label_text:
                code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=20).next_to({var_name}, DOWN)')
        
        elif obj_type == "vector":
            end = props.get("end", [position[0] + 2, position[1]])
            code_lines.append(f'{var_name} = Arrow(start=np.array([{position[0]}, {position[1]}, 0]), end=np.array([{end[0]}, {end[1]}, 0]), color={color}, buff=0)')
            if label_text:
                code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=20).next_to({var_name}, DOWN)')
        
        elif obj_type == "equation":
            latex = props.get("latex", "E = mc^2")
            pos_name = POSITION_MAP.get(props.get("position", "center"), "ORIGIN")
            code_lines.append(f'{var_name} = MathTex(r"{latex}").move_to({pos_name})')
        
        elif obj_type == "label":
            text = props.get("text", label_text or obj_id)
            font_size = props.get("font_size", 28)
            if isinstance(position, list):
                code_lines.append(f'{var_name} = Text("{text}", font_size={font_size}).move_to(np.array([{position[0]}, {position[1]}, 0]))')
            else:
                pos_name = POSITION_MAP.get(position, "ORIGIN")
                code_lines.append(f'{var_name} = Text("{text}", font_size={font_size}).move_to({pos_name})')
        
        elif obj_type == "axes":
            x_range = props.get("x_range", [-3, 3, 1])
            y_range = props.get("y_range", [-3, 3, 1])
            if len(x_range) == 2:
                x_range = [x_range[0], x_range[1], 1]
            if len(y_range) == 2:
                y_range = [y_range[0], y_range[1], 1]
            code_lines.append(f'{var_name} = Axes(x_range=[{x_range[0]}, {x_range[1]}, {x_range[2]}], y_range=[{y_range[0]}, {y_range[1]}, {y_range[2]}], x_length=8, y_length=6, axis_config={{"include_tip": True}})')
        
        elif obj_type == "graph":
            equation = props.get("equation", "lambda x: x**2")
            graph_color = COLOR_MAP.get(props.get("color", "blue").lower(), "BLUE")
            axes_var = props.get("axes", "axes")
            code_lines.append(f'{var_name} = {axes_var}.plot({equation}, color={graph_color})')
        
        elif obj_type == "area_under_graph":
            graph_id = props.get("graph_id", "graph")
            graph_var = object_vars.get(graph_id, graph_id)
            x_range = props.get("x_range", [0, 2])
            axes_var = props.get("axes", "axes")
            fill_color = props.get("color", "#87CEEB")
            opacity = props.get("opacity", 0.5)
            code_lines.append(f'{var_name} = {axes_var}.get_area({graph_var}, x_range=[{x_range[0]}, {x_range[1]}], color="{fill_color}", opacity={opacity})')
        
        elif obj_type == "recap_panel" or obj_type == "panel":
            title = props.get("title", "")
            visual = props.get("visual", "")
            formula = props.get("formula", "")
            if isinstance(position, list):
                pos_str = f"np.array([{position[0]}, {position[1]}, 0])"
            else:
                pos_str = POSITION_MAP.get(position, "ORIGIN")
            content = f"{title}\\n{visual}\\n{formula}" if visual else title
            code_lines.append(f'{var_name} = VGroup(Rectangle(width=4, height=3, color=BLUE), Text("{content[:50]}", font_size=20)).move_to({pos_str})')
        
        elif obj_type == "text":
            text = props.get("text", label_text or obj_id)
            font_size = props.get("font_size", 24)
            if isinstance(position, list):
                code_lines.append(f'{var_name} = Text("{text}", font_size={font_size}).move_to(np.array([{position[0]}, {position[1]}, 0]))')
            else:
                pos_name = POSITION_MAP.get(position, "ORIGIN")
                code_lines.append(f'{var_name} = Text("{text}", font_size={font_size}).move_to({pos_name})')
        
        else:
            if isinstance(position, list):
                code_lines.append(f'{var_name} = Dot(point=np.array([{position[0]}, {position[1]}, 0]), color={color})')
            else:
                pos_name = POSITION_MAP.get(position, "ORIGIN")
                code_lines.append(f'{var_name} = Dot(point={pos_name}, color={color})')
    
    forces = spec.get("forces", [])
    for force in forces:
        force_id = force["id"]
        from_obj = force.get("from_object")
        to_obj = force.get("to_object")
        direction = force.get("direction", "repulsive")
        color = COLOR_MAP.get(force.get("color", "red").lower(), "RED")
        label_text = force.get("label", "")
        
        var_name = force_id.replace("-", "_").replace(" ", "_")
        object_vars[force_id] = var_name
        
        from_var = object_vars.get(from_obj, "ORIGIN")
        to_var = object_vars.get(to_obj, "ORIGIN")
        
        if direction == "repulsive":
            code_lines.append(f'{var_name}_start = {from_var}.get_center()')
            code_lines.append(f'{var_name}_dir = ({from_var}.get_center() - {to_var}.get_center())')
            code_lines.append(f'{var_name}_dir = {var_name}_dir / np.linalg.norm({var_name}_dir) * 1.5')
            code_lines.append(f'{var_name} = Arrow(start={var_name}_start, end={var_name}_start + {var_name}_dir, color={color}, buff=0.1)')
        elif direction == "attractive":
            code_lines.append(f'{var_name}_start = {from_var}.get_center()')
            code_lines.append(f'{var_name}_dir = ({to_var}.get_center() - {from_var}.get_center())')
            code_lines.append(f'{var_name}_dir = {var_name}_dir / np.linalg.norm({var_name}_dir) * 1.5')
            code_lines.append(f'{var_name} = Arrow(start={var_name}_start, end={var_name}_start + {var_name}_dir, color={color}, buff=0.1)')
        else:
            code_lines.append(f'{var_name} = Arrow(start={from_var}.get_center(), end={to_var}.get_center(), color={color}, buff=0.1)')
        
        if label_text:
            code_lines.append(f'{var_name}_label = Text("{label_text}", font_size=20).next_to({var_name}, UP)')
    
    equations = spec.get("equations", [])
    for eq in equations:
        eq_id = eq["id"]
        latex = eq.get("latex", "")
        position = eq.get("position", "top_center")
        
        var_name = eq_id.replace("-", "_").replace(" ", "_")
        object_vars[eq_id] = var_name
        
        if isinstance(position, list):
            pos_name = f"np.array([{position[0] if len(position) > 0 else 0}, {position[1] if len(position) > 1 else 0}, 0])"
        else:
            pos_name = POSITION_MAP.get(position, "UP * 3")
        code_lines.append(f'{var_name} = MathTex(r"{latex}").move_to({pos_name})')
        
        if eq.get("substitution"):
            sub_latex = eq["substitution"]
            code_lines.append(f'{var_name}_sub = MathTex(r"{sub_latex}").move_to({pos_name})')
    
    code_lines.append("")
    code_lines.append("# Animation sequence")
    
    animation_sequence = spec.get("animation_sequence", [])
    for anim in animation_sequence:
        action = anim.get("action", "appear")
        target = anim.get("target") or ""
        duration = anim.get("duration", 1.0)
        
        if not target and action != "wait":
            continue
        
        target_var = object_vars.get(target, target.replace("-", "_").replace(" ", "_")) if target else "placeholder"
        
        if action == "appear":
            code_lines.append(f'self.play(FadeIn({target_var}), run_time={duration})')
            if f'{target_var}_label' in '\n'.join(code_lines):
                code_lines.append(f'self.play(FadeIn({target_var}_label), run_time=0.3)')
        
        elif action == "draw_force":
            code_lines.append(f'self.play(GrowArrow({target_var}), run_time={duration})')
            if f'{target_var}_label' in '\n'.join(code_lines):
                code_lines.append(f'self.play(FadeIn({target_var}_label), run_time=0.3)')
        
        elif action == "show_equation":
            code_lines.append(f'self.play(Write({target_var}), run_time={duration})')
        
        elif action == "substitute":
            code_lines.append(f'self.play(TransformMatchingShapes({target_var}, {target_var}_sub), run_time={duration})')
        
        elif action == "highlight":
            code_lines.append(f'self.play(Indicate({target_var}), run_time={duration})')
        
        elif action == "move":
            new_pos = anim.get("to", [0, 0])
            code_lines.append(f'self.play({target_var}.animate.move_to(np.array([{new_pos[0]}, {new_pos[1]}, 0])), run_time={duration})')
        
        elif action == "transform":
            to_target = anim.get("to") or ""
            if to_target:
                to_var = object_vars.get(to_target, to_target.replace("-", "_").replace(" ", "_"))
                code_lines.append(f'self.play(Transform({target_var}, {to_var}), run_time={duration})')
        
        elif action == "wait":
            code_lines.append(f'self.wait({duration})')
        
        elif action == "draw":
            code_lines.append(f'self.play(Create({target_var}), run_time={duration})')
        
        elif action == "fill":
            code_lines.append(f'self.play(FadeIn({target_var}), run_time={duration})')
        
        elif action == "write":
            code_lines.append(f'self.play(Write({target_var}), run_time={duration})')
        
        elif action == "grow":
            code_lines.append(f'self.play(GrowFromCenter({target_var}), run_time={duration})')
        
        elif action == "fade_out":
            code_lines.append(f'self.play(FadeOut({target_var}), run_time={duration})')
        
        else:
            code_lines.append(f'self.play(FadeIn({target_var}), run_time={duration})')
    
    code_lines.append('self.wait(1)')
    
    return '\n'.join(code_lines)


def compile_manim_plan(beat: dict, section_id: int, beat_index: int) -> dict:
    """Compile a Manim animation plan from structured visual beat fields.
    
    REQUIRES: manim_scene_spec JSON with objects, forces, equations, animation_sequence.
    FAIL-FAST: Raises VisualCompilationError if manim_scene_spec is missing or invalid.
    """
    validate_visual_beat_structure(beat, section_id, beat_index)
    
    manim_scene_spec = beat.get("manim_scene_spec")
    
    if manim_scene_spec:
        manim_code = translate_spec_to_manim_code(manim_scene_spec, section_id, beat_index)
        
        return {
            "scene_type": "spec_generated",
            "manim_code": manim_code,
            "spec": manim_scene_spec,
            "params": {
                "generated_code": manim_code,
                "object_count": len(manim_scene_spec.get("objects", [])),
                "force_count": len(manim_scene_spec.get("forces", [])),
                "equation_count": len(manim_scene_spec.get("equations", [])),
                "animation_count": len(manim_scene_spec.get("animation_sequence", []))
            }
        }
    
    raise VisualCompilationError(
        section_id, beat_index,
        "Manim section missing manim_scene_spec. For renderer=manim, each visual_beat must include a structured "
        "manim_scene_spec JSON with objects, forces, equations, and animation_sequence. "
        "Prose-only descriptions are not allowed for Manim sections."
    )


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
