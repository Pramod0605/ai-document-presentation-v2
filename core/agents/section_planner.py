"""
V1.5 Section Planner Agent (REQ-010)

Takes topics from Chunker, outputs section blueprints with metadata.
Each blueprint defines: section type, title, renderer choice, avatar settings.
"""
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent


class SectionPlannerAgent(BaseAgent):
    """
    Section Planner Agent - Plans the presentation structure.
    
    Input: topics (from Chunker), subject, grade
    Output: Array of SectionBlueprint objects
    """
    
    name = "SectionPlanner"
    system_prompt_file = "section_planner_system_v1.5.txt"
    user_prompt_file = "section_planner_user_v1.5.txt"
    output_schema_file = "section_blueprint.schema.json"
    model = "google/gemini-2.5-flash"
    temperature = 0.3
    max_tokens = 8000
    
    def validate_structural(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate the sections array structure."""
        errors = []
        
        if "sections" not in output:
            errors.append("Missing 'sections' array")
            return False, errors
        
        sections = output.get("sections", [])
        if not isinstance(sections, list) or len(sections) == 0:
            errors.append("'sections' must be a non-empty array")
            return False, errors
        
        required_fields = [
            "section_id", "section_type", "title", "source_topics",
            "learning_goals", "suggested_renderer", "renderer_reasoning",
            "avatar_visibility", "avatar_position", "estimated_duration_seconds"
        ]
        
        valid_section_types = ["intro", "summary", "content", "example", "quiz", "memory", "recap"]
        valid_renderers = ["manim", "remotion", "video", "none"]
        valid_visibility = ["required", "optional", "hidden"]
        valid_positions = ["left", "right", "center", "hidden"]
        
        for i, section in enumerate(sections):
            for field in required_fields:
                if field not in section:
                    errors.append(f"Section {i}: missing required field '{field}'")
            
            if "section_type" in section and section["section_type"] not in valid_section_types:
                errors.append(f"Section {i}: invalid section_type '{section.get('section_type')}'")
            
            if "suggested_renderer" in section and section["suggested_renderer"] not in valid_renderers:
                errors.append(f"Section {i}: invalid suggested_renderer '{section.get('suggested_renderer')}'")
            
            if "avatar_visibility" in section and section["avatar_visibility"] not in valid_visibility:
                errors.append(f"Section {i}: invalid avatar_visibility '{section.get('avatar_visibility')}'")
            
            if "avatar_position" in section and section["avatar_position"] not in valid_positions:
                errors.append(f"Section {i}: invalid avatar_position '{section.get('avatar_position')}'")
        
        return len(errors) == 0, errors
    
    def validate_semantic(self, output: Dict[str, Any], input_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate semantic rules for section planning."""
        errors = []
        sections = output.get("sections", [])
        
        section_types = [s.get("section_type") for s in sections]
        
        if section_types.count("intro") != 1:
            errors.append(f"Must have exactly 1 intro section, found {section_types.count('intro')}")
        
        if section_types.count("summary") != 1:
            errors.append(f"Must have exactly 1 summary section, found {section_types.count('summary')}")
        
        if sections and sections[0].get("section_type") != "intro":
            errors.append("First section must be 'intro'")
        
        if sections and len(sections) > 1 and sections[1].get("section_type") != "summary":
            errors.append("Second section must be 'summary'")
        
        content_count = section_types.count("content") + section_types.count("example")
        if content_count < 1:
            errors.append("Must have at least 1 content or example section")
        
        for i, section in enumerate(sections):
            st = section.get("section_type")
            renderer = section.get("suggested_renderer")
            
            if st in ["intro", "summary", "memory"] and renderer != "none":
                errors.append(f"Section {i} ({st}): renderer must be 'none' for {st} sections")
            
            if st == "recap" and renderer != "video":
                errors.append(f"Section {i} (recap): renderer must be 'video' for recap sections")
        
        return len(errors) == 0, errors
