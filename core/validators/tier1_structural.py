"""
Tier 1 - STRUCTURAL HARD FAIL Validator (Compiler Errors)

Purpose: Guarantee output is structurally executable by pipeline + player.
If Tier 1 fails → STOP IMMEDIATELY. NO RETRY FOR CONTENT.

Tier-1 checks (HARD FAIL):
- Sections & ordering: missing intro/summary/memory/recap
- Core structure: missing renderer, missing visual_beats, missing display_directives
- Counts: recap scenes ≠ 5, memory flashcards ≠ 5
- Layer logic: text + complex visual visible simultaneously
- Renderer contracts: manim without manim_scene_spec, etc.
"""

from typing import List, Dict, Any, Tuple

REQUIRED_SECTION_TYPES = ["intro", "summary", "memory", "recap"]
RECAP_SCENE_COUNT = 5
MEMORY_FLASHCARD_COUNT = 5


class StructuralError:
    """Structural validation error - causes hard fail."""
    def __init__(self, code: str, section_id: int, details: str):
        self.code = code
        self.section_id = section_id
        self.details = details
    
    def __str__(self):
        return f"[STRUCTURAL] {self.code} (section {self.section_id}): {self.details}"


def validate_structural(presentation: dict) -> List[StructuralError]:
    """
    Run all Tier-1 structural checks.
    
    Returns list of StructuralError (empty if valid).
    """
    errors = []
    sections = presentation.get("sections", [])
    
    errors.extend(_check_required_sections(sections))
    errors.extend(_check_section_counts(sections))
    
    for section in sections:
        errors.extend(_check_section_structure(section))
        errors.extend(_check_display_directives(section))
        errors.extend(_check_layer_logic(section))
        errors.extend(_check_renderer_contracts(section))
        errors.extend(_check_avatar_rules(section))
    
    return errors


def _check_required_sections(sections: List[Dict]) -> List[StructuralError]:
    """Check mandatory sections exist."""
    errors = []
    section_types = [s.get("section_type") for s in sections]
    
    for required_type in REQUIRED_SECTION_TYPES:
        if required_type not in section_types:
            errors.append(StructuralError(
                f"missing_{required_type}_section",
                0,
                f"Presentation is missing required '{required_type}' section"
            ))
    
    return errors


def _check_section_counts(sections: List[Dict]) -> List[StructuralError]:
    """Check recap scene count = 5, memory flashcard count = 5."""
    errors = []
    
    for section in sections:
        section_id = section.get("section_id") or section.get("id", 0)
        section_type = section.get("section_type", "")
        
        if section_type == "recap":
            recap_scenes = section.get("recap_scenes", [])
            if not recap_scenes:
                recap_scenes = section.get("visual_beats", [])
            if len(recap_scenes) != RECAP_SCENE_COUNT:
                errors.append(StructuralError(
                    "recap_scene_count_wrong",
                    section_id,
                    f"Recap has {len(recap_scenes)} scenes, must be exactly {RECAP_SCENE_COUNT}"
                ))
        
        if section_type == "memory":
            flashcards = section.get("flashcards", [])
            if not flashcards:
                flashcards = section.get("visual_beats", [])
            if len(flashcards) != MEMORY_FLASHCARD_COUNT:
                errors.append(StructuralError(
                    "memory_flashcard_count_wrong",
                    section_id,
                    f"Memory has {len(flashcards)} flashcards, must be exactly {MEMORY_FLASHCARD_COUNT}"
                ))
    
    return errors


def _check_section_structure(section: Dict) -> List[StructuralError]:
    """Check core structure: renderer present, visual_beats present for content/example."""
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    renderer = section.get("renderer")
    
    if not renderer:
        errors.append(StructuralError(
            "missing_renderer",
            section_id,
            f"Section type '{section_type}' has no renderer specified"
        ))
    
    if section_type in ["content", "example"]:
        visual_beats = section.get("visual_beats", [])
        narration_segments = section.get("narration_segments", [])
        narration = section.get("narration", {})
        if isinstance(narration, dict):
            narration_segments = narration_segments or narration.get("segments", [])
        
        embedded_visual_beats = [
            seg.get("visual_beat") for seg in narration_segments 
            if seg.get("visual_beat")
        ]
        
        effective_beats = visual_beats if visual_beats else embedded_visual_beats
        
        if not effective_beats:
            errors.append(StructuralError(
                "missing_visual_beats",
                section_id,
                f"Section type '{section_type}' has no visual_beats"
            ))
    
    return errors


def _check_display_directives(section: Dict) -> List[StructuralError]:
    """Check display_directives structure exists and has required layers."""
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    
    display_directives = section.get("display_directives", [])
    narration = section.get("narration", {})
    narration_segments = []
    if isinstance(narration, dict):
        narration_segments = narration.get("segments", [])
    
    if narration_segments and not display_directives:
        errors.append(StructuralError(
            "missing_display_directives",
            section_id,
            f"Section has {len(narration_segments)} narration segments but no display_directives array"
        ))
        return errors
    
    if display_directives is None:
        errors.append(StructuralError(
            "display_directives_null",
            section_id,
            "display_directives is null (must be array)"
        ))
        return errors
    
    if narration_segments and len(display_directives) != len(narration_segments):
        errors.append(StructuralError(
            "display_directives_count_mismatch",
            section_id,
            f"display_directives count ({len(display_directives)}) != narration segments ({len(narration_segments)})"
        ))
    
    for i, dd in enumerate(display_directives):
        if not isinstance(dd, dict):
            errors.append(StructuralError(
                "invalid_display_directive",
                section_id,
                f"display_directive {i} must be an object"
            ))
            continue
        
        required_layers = ["text_layer", "visual_layer", "avatar_layer"]
        for layer in required_layers:
            layer_obj = dd.get(layer)
            if layer_obj is None:
                errors.append(StructuralError(
                    "missing_layer_in_directive",
                    section_id,
                    f"display_directive {i} missing '{layer}'"
                ))
            elif not isinstance(layer_obj, dict):
                errors.append(StructuralError(
                    "invalid_layer_in_directive",
                    section_id,
                    f"display_directive {i} '{layer}' must be an object with 'action'"
                ))
            elif "action" not in layer_obj:
                errors.append(StructuralError(
                    "missing_action_in_layer",
                    section_id,
                    f"display_directive {i} '{layer}' missing 'action' field"
                ))
    
    return errors


def _check_layer_logic(section: Dict) -> List[StructuralError]:
    """Check text + complex visual not shown simultaneously."""
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    
    display_directives = section.get("display_directives", [])
    
    for i, dd in enumerate(display_directives):
        if not isinstance(dd, dict):
            continue
        
        text_layer = dd.get("text_layer", {})
        visual_layer = dd.get("visual_layer", {})
        
        text_action = text_layer.get("action") if isinstance(text_layer, dict) else text_layer
        visual_action = visual_layer.get("action") if isinstance(visual_layer, dict) else visual_layer
        
        if text_action == "show" and visual_action in ["show", "replace"]:
            errors.append(StructuralError(
                "text_and_visuals_simultaneous",
                section_id,
                f"Directive {i}: text_layer=show + visual_layer={visual_action} violates mutual exclusion"
            ))
    
    return errors


def _check_renderer_contracts(section: Dict) -> List[StructuralError]:
    """Check renderer-specific specs are present."""
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    renderer = section.get("renderer", "")
    
    if section_type not in ["content", "example"]:
        return errors
    
    if renderer == "manim":
        section_manim_spec = section.get("manim_scene_spec")
        
        if section_manim_spec:
            objects = section_manim_spec.get("objects", [])
            equations = section_manim_spec.get("equations", [])
            forces = section_manim_spec.get("forces", [])
            animation_seq = section_manim_spec.get("animation_sequence", [])
            
            if not objects and not equations and not forces:
                errors.append(StructuralError(
                    "manim_no_renderable_content",
                    section_id,
                    "manim_scene_spec has no objects/equations/forces"
                ))
            if not animation_seq:
                errors.append(StructuralError(
                    "manim_no_animation_sequence",
                    section_id,
                    "manim_scene_spec has no animation_sequence"
                ))
        else:
            visual_beats = section.get("visual_beats", [])
            has_beat_level_spec = any(
                beat.get("manim_scene_spec") for beat in visual_beats 
                if isinstance(beat, dict)
            )
            if not has_beat_level_spec:
                errors.append(StructuralError(
                    "manim_section_without_scene_spec",
                    section_id,
                    "Manim section has no manim_scene_spec"
                ))
    
    if renderer == "remotion" and section_type in ["content", "example"]:
        if not section.get("remotion_scene_spec"):
            errors.append(StructuralError(
                "remotion_section_without_scene_spec",
                section_id,
                "Remotion section has no remotion_scene_spec"
            ))
    
    if renderer in ["video", "wan", "wan_video"] and section_type in ["content", "example"]:
        if not section.get("video_prompts") and not section.get("recap_scenes"):
            errors.append(StructuralError(
                "video_section_without_prompts",
                section_id,
                "Video section has no video_prompts"
            ))
    
    return errors


def _check_avatar_rules(section: Dict) -> List[StructuralError]:
    """Check avatar visibility rules per section type."""
    errors = []
    section_id = section.get("section_id") or section.get("id", 0)
    section_type = section.get("section_type", "")
    layout = section.get("layout", {})
    avatar_zone = layout.get("avatar_zone", {})
    display_directives = section.get("display_directives", [])
    
    if section_type == "intro":
        avatar_mode = avatar_zone.get("mode", "")
        avatar_width = avatar_zone.get("width_percent", 0)
        avatar_visibility = avatar_zone.get("visibility", "visible")
        
        if avatar_visibility == "hidden" or avatar_mode == "hidden":
            errors.append(StructuralError(
                "intro_avatar_not_visible",
                section_id,
                "Intro avatar_zone must be visible"
            ))
        elif avatar_width and avatar_width < 50:
            errors.append(StructuralError(
                "intro_avatar_too_small",
                section_id,
                f"Intro avatar width is {avatar_width}%, must be ≥50%"
            ))
        
        for i, dd in enumerate(display_directives):
            if isinstance(dd, dict):
                avatar_layer = dd.get("avatar_layer", {})
                avatar_action = avatar_layer.get("action") if isinstance(avatar_layer, dict) else avatar_layer
                if avatar_action == "hide":
                    errors.append(StructuralError(
                        "intro_avatar_hidden_in_segment",
                        section_id,
                        f"Intro directive {i}: avatar cannot be 'hide'"
                    ))
    
    if section_type == "recap":
        avatar_mode = avatar_zone.get("mode", "")
        avatar_visibility = avatar_zone.get("visibility", "")
        
        if avatar_mode not in ["hidden", ""] and avatar_visibility != "hidden":
            if avatar_zone:
                errors.append(StructuralError(
                    "recap_avatar_visible",
                    section_id,
                    "Recap avatar_zone must be hidden (video only)"
                ))
        
        for i, dd in enumerate(display_directives):
            if isinstance(dd, dict):
                avatar_layer = dd.get("avatar_layer", {})
                avatar_action = avatar_layer.get("action") if isinstance(avatar_layer, dict) else avatar_layer
                if avatar_action in ["show", "gesture_only"]:
                    errors.append(StructuralError(
                        "recap_avatar_visible_in_segment",
                        section_id,
                        f"Recap directive {i}: avatar must be 'hide', not '{avatar_action}'"
                    ))
    
    return errors


def format_structural_errors(errors: List[StructuralError]) -> str:
    """Format structural errors for logging/retry prompt."""
    if not errors:
        return ""
    
    lines = ["STRUCTURAL ERRORS (Tier 1 - Hard Fail):"]
    for err in errors:
        lines.append(f"  - {err}")
    return "\n".join(lines)
