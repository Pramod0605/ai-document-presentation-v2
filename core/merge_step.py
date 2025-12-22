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
    5. recap (SINGLE section with 5 scenes merged from recap_scene_1..5)
    
    IMPORTANT: The player expects ONE 'recap' section with visual_beats/recap_scenes array.
    The Split Director outputs 5 separate recap_scene_N sections which we MERGE here
    into a single player-compatible recap section.
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
    recap_scene_sections = {}
    
    for section in recap_sections:
        section_type = section.get("section_type")
        if section_type == "memory":
            memory = section
        elif section_type in RECAP_SCENE_ORDER:
            recap_scene_sections[section_type] = section
    
    if memory:
        ordered.append(memory)
    
    merged_recap = _merge_recap_scenes_to_single_section(recap_scene_sections)
    if merged_recap:
        ordered.append(merged_recap)
    
    return ordered


def _merge_recap_scenes_to_single_section(recap_scene_sections: Dict[str, Dict]) -> Optional[Dict]:
    """
    Convert 5 separate recap_scene_N sections into ONE 'recap' section.
    
    This maintains player compatibility while allowing the LLM to generate
    smaller, more manageable sections.
    
    Input: {"recap_scene_1": {...}, "recap_scene_2": {...}, ...}
    Output: Single section with section_type="recap" containing:
      - Merged narration from all scenes
      - visual_beats array with all scene prompts
      - recap_scenes array for video paths
    """
    if not recap_scene_sections:
        logger.warning("[Merge Step] No recap scenes to merge")
        return None
    
    all_narration_text = []
    all_segments = []
    visual_beats = []
    recap_scenes = []
    total_duration = 0.0
    
    for scene_type in RECAP_SCENE_ORDER:
        if scene_type not in recap_scene_sections:
            logger.warning(f"[Merge Step] Missing {scene_type}")
            continue
        
        scene = recap_scene_sections[scene_type]
        scene_index = RECAP_SCENE_ORDER.index(scene_type) + 1
        
        narration = scene.get("narration", {})
        scene_text = narration.get("full_text", "") or scene.get("narration_text", "")
        if scene_text:
            all_narration_text.append(scene_text)
        
        segments = narration.get("segments", [])
        for seg in segments:
            adjusted_seg = seg.copy()
            adjusted_seg["start_time"] = adjusted_seg.get("start_time", 0) + total_duration
            adjusted_seg["end_time"] = adjusted_seg.get("end_time", 0) + total_duration
            all_segments.append(adjusted_seg)
        
        scene_duration = narration.get("total_duration", 0) or scene.get("duration", 30)
        
        video_prompt = scene.get("video_prompt", "")
        if isinstance(video_prompt, dict):
            video_prompt = video_prompt.get("prompt", "") or video_prompt.get("description", "")
        
        visual_beats.append({
            "scene_id": scene_index,
            "time": total_duration,
            "description": video_prompt,
            "video_prompt": video_prompt,
            "duration": scene_duration
        })
        
        recap_scenes.append({
            "scene_id": scene_index,
            "scene": scene_index,
            "wan_prompt": video_prompt,
            "video_prompt": video_prompt,
            "narration_text": scene_text,
            "duration": scene_duration
        })
        
        total_duration += scene_duration
    
    if not visual_beats:
        logger.warning("[Merge Step] No visual beats generated from recap scenes")
        return None
    
    merged_recap = {
        "section_type": "recap",
        "section_title": "Lesson Recap",
        "layout": "avatar_hidden",
        "renderer": "video",
        "renderer_reasoning": "WAN video for cinematic recap visualization",
        "narration": {
            "full_text": " ".join(all_narration_text),
            "segments": all_segments,
            "total_duration": total_duration
        },
        "visual_beats": visual_beats,
        "recap_scenes": recap_scenes,
        "avatar": {
            "visible": False,
            "position": "hidden"
        }
    }
    
    logger.info(f"[Merge Step] Merged {len(visual_beats)} recap scenes into single recap section (duration: {total_duration}s)")
    return merged_recap


def _validate_merged_output(presentation: Dict) -> None:
    """
    Final validation of merged output.
    Logs warnings for any issues but doesn't raise errors
    (validation should have been done by Directors).
    
    NOTE: After merging, recap_scene_1..5 become ONE 'recap' section.
    """
    sections = presentation.get("sections", [])
    section_types = [s.get("section_type") for s in sections]
    
    required_types = ["intro", "summary", "memory", "recap"]
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
