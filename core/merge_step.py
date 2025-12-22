"""
Merge Step v1.4 - Deterministic Output Combination

Merges Content Director output + Recap Director output into a single
presentation.json that is v1.3 schema compliant.

This is pure Python logic - NO LLM calls.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def merge_director_outputs(
    content_output: Dict,
    recap_output: Dict,
    subject: str,
    grade: str
) -> Dict:
    """
    Deterministic merge of Content Director + Recap Director outputs.
    No LLM calls - pure Python logic.
    
    Operations:
    1. Combine sections array: content_sections + [memory, recap]
    2. Assign sequential section_ids
    3. Preserve all fields from both outputs
    4. Set spec_version: "v1.4"
    5. Add generation metadata
    
    Args:
        content_output: Output from Content Director (intro/summary/content/example/quiz)
        recap_output: Output from Recap Director (memory/recap)
        subject: Subject area
        grade: Grade level
        
    Returns:
        Complete presentation.json dict (v1.3 schema compliant)
    """
    logger.info("[Merge Step] Combining Content + Recap Director outputs")
    
    content_sections = content_output.get("sections", [])
    recap_sections = recap_output.get("sections", [])
    
    logger.info(f"[Merge Step] Content sections: {len(content_sections)}, Recap sections: {len(recap_sections)}")
    
    ordered_sections = _order_sections(content_sections, recap_sections)
    
    for i, section in enumerate(ordered_sections, start=1):
        section["section_id"] = f"section_{i}"
    
    title = content_output.get("title", f"{subject} Lesson")
    
    presentation = {
        "spec_version": "v1.4",
        "title": title,
        "subject": subject,
        "grade": grade,
        "sections": ordered_sections,
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "pipeline_version": "v1.4",
            "content_director_model": "google/gemini-2.5-pro",
            "recap_director_model": "google/gemini-2.5-pro",
            "section_count": len(ordered_sections),
            "section_types": [s.get("section_type") for s in ordered_sections]
        }
    }
    
    _validate_merged_output(presentation)
    
    logger.info(f"[Merge Step] Successfully merged {len(ordered_sections)} sections")
    return presentation


RECAP_SCENE_ORDER = ["recap_scene_1", "recap_scene_2", "recap_scene_3", "recap_scene_4", "recap_scene_5"]


def _order_sections(content_sections: List[Dict], recap_sections: List[Dict]) -> List[Dict]:
    """
    Order sections in pedagogical sequence:
    1. intro
    2. summary
    3. content/example/quiz (in original order)
    4. memory
    5. recap_scene_1 through recap_scene_5 (in order)
    """
    ordered = []
    
    intro = None
    summary = None
    other_content = []
    
    for section in content_sections:
        section_type = section.get("section_type")
        if section_type == "intro":
            intro = section
        elif section_type == "summary":
            summary = section
        else:
            other_content.append(section)
    
    if intro:
        ordered.append(intro)
    if summary:
        ordered.append(summary)
    
    ordered.extend(other_content)
    
    memory = None
    recap_scenes = {}
    
    for section in recap_sections:
        section_type = section.get("section_type")
        if section_type == "memory":
            memory = section
        elif section_type in RECAP_SCENE_ORDER:
            recap_scenes[section_type] = section
    
    if memory:
        ordered.append(memory)
    
    for scene_type in RECAP_SCENE_ORDER:
        if scene_type in recap_scenes:
            ordered.append(recap_scenes[scene_type])
    
    return ordered


def _validate_merged_output(presentation: Dict) -> None:
    """
    Final validation of merged output.
    Logs warnings for any issues but doesn't raise errors
    (validation should have been done by Directors).
    """
    sections = presentation.get("sections", [])
    section_types = [s.get("section_type") for s in sections]
    
    required_types = ["intro", "summary", "memory"] + RECAP_SCENE_ORDER
    missing = [t for t in required_types if t not in section_types]
    
    if missing:
        logger.warning(f"[Merge Step] Warning: Missing required section types: {missing}")
    
    content_count = sum(1 for t in section_types if t in ["content", "example"])
    if content_count == 0:
        logger.warning("[Merge Step] Warning: No content or example sections found")
    
    for i, section in enumerate(sections):
        if "section_id" not in section:
            logger.warning(f"[Merge Step] Section {i} missing section_id")
        if "renderer" not in section:
            logger.warning(f"[Merge Step] Section {i} missing renderer")
        if "narration" not in section:
            logger.warning(f"[Merge Step] Section {i} missing narration")


def get_section_stats(presentation: Dict) -> Dict:
    """
    Get statistics about the merged presentation.
    
    Returns:
        Dict with section counts and types
    """
    sections = presentation.get("sections", [])
    
    type_counts = {}
    renderer_counts = {}
    total_segments = 0
    
    for section in sections:
        section_type = section.get("section_type", "unknown")
        renderer = section.get("renderer", "unknown")
        
        type_counts[section_type] = type_counts.get(section_type, 0) + 1
        renderer_counts[renderer] = renderer_counts.get(renderer, 0) + 1
        
        segments = section.get("narration", {}).get("segments", [])
        total_segments += len(segments)
    
    return {
        "total_sections": len(sections),
        "total_segments": total_segments,
        "section_types": type_counts,
        "renderers": renderer_counts
    }
