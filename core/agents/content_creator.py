"""
V1.5 ContentCreator Agent - Combined Narration + Visual Specification

Optimization: Combines NarrationWriter + VisualSpecArtist into single LLM call.
This reduces 2 LLM calls per section to 1, with coupled visual+narration output.

V3 Integration:
- Uses persona-based narration (Namaste intro, quizmaster for quiz, etc.)
- Detects Q&A pairs and marks display_format: flashcard
- Ensures avatar always visible
- Word count limits from V3

Output is compatible with existing MergeStep - produces same fields.
"""
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent, STRONG_MODEL


class ContentCreatorAgent(BaseAgent):
    """
    ContentCreator Agent - Creates coupled narration + visual specs.
    
    Input: section_blueprint, source_markdown, quiz_questions (optional)
    Output: section_id, narration, visual_beats, segment_enrichments
    
    Replaces: NarrationWriterAgent + VisualSpecArtistAgent (2 LLM calls → 1)
    """
    
    name = "ContentCreator"
    system_prompt_file = "content_creator_system_v1.5.txt"
    user_prompt_file = "content_creator_user_v1.5.txt"
    output_schema_file = "content_creator.schema.json"
    model = "google/gemini-2.5-flash"
    temperature = 0.5
    max_tokens = 12000
    structural_retries = 2
    semantic_retries = 2
    
    WORD_LIMITS = {
        "intro": (40, 80),
        "summary": (60, 150),
        "content": (100, 300),
        "example": (100, 300),
        "quiz": (80, 250),
        "memory": (30, 100),
        "recap": (150, 350)
    }
    
    SEGMENT_LIMITS = {
        "intro": (1, 1),      # Single greeting segment
        "summary": (1, 2),    # Brief overview only
        "content": (2, 50),   # No practical upper limit - extract ALL source content
        "example": (2, 50),   # No practical upper limit - extract ALL examples
        "quiz": (2, 50),      # No practical upper limit - extract ALL quiz questions
        "memory": (3, 3),     # Fixed: 3 flashcards
        "recap": (5, 5)       # Fixed: 5 video scenes
    }
    
    def validate_structural(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate combined output structure."""
        errors = []
        
        if "section_id" not in output:
            errors.append("Missing 'section_id'")
        
        if "narration" not in output:
            errors.append("Missing 'narration' object")
        else:
            narration = output.get("narration", {})
            
            if "full_text" not in narration:
                errors.append("Missing 'narration.full_text'")
            
            if "segments" not in narration:
                errors.append("Missing 'narration.segments' array")
            else:
                segments = narration.get("segments", [])
                if not isinstance(segments, list) or len(segments) == 0:
                    errors.append("'narration.segments' must be a non-empty array")
                else:
                    segment_ids = []
                    for i, seg in enumerate(segments):
                        if "segment_id" not in seg:
                            errors.append(f"Segment {i}: missing 'segment_id'")
                        else:
                            segment_ids.append(seg["segment_id"])
                        
                        if "text" not in seg:
                            errors.append(f"Segment {i}: missing 'text'")
                        elif len(seg.get("text", "")) < 10:
                            errors.append(f"Segment {i}: text too short (min 10 chars)")
                        
                        if "duration_seconds" not in seg:
                            errors.append(f"Segment {i}: missing 'duration_seconds'")
                    
                    expected_ids = list(range(1, len(segments) + 1))
                    if sorted(segment_ids) != expected_ids:
                        errors.append(f"segment_ids must be sequential 1 to {len(segments)}, got {segment_ids}")
        
        if "visual_beats" not in output:
            errors.append("Missing 'visual_beats' array")
        else:
            beats = output.get("visual_beats", [])
            valid_types = ["diagram", "formula", "process", "video_clip", "text_only", "animation", "flashcard"]
            
            for i, beat in enumerate(beats):
                if "beat_id" not in beat:
                    errors.append(f"Beat {i}: missing 'beat_id'")
                elif not isinstance(beat.get("beat_id"), str):
                    errors.append(f"Beat {i}: 'beat_id' must be a string")
                
                if "segment_id" not in beat:
                    errors.append(f"Beat {i}: missing 'segment_id'")
                elif not isinstance(beat.get("segment_id"), int):
                    errors.append(f"Beat {i}: 'segment_id' must be an integer")
                
                if "visual_beat_type" not in beat:
                    errors.append(f"Beat {i}: missing 'visual_beat_type'")
                elif beat.get("visual_beat_type") not in valid_types:
                    errors.append(f"Beat {i}: invalid visual_beat_type '{beat.get('visual_beat_type')}'")
                
                if "description" not in beat:
                    errors.append(f"Beat {i}: missing 'description'")
                elif len(beat.get("description", "")) < 10:
                    errors.append(f"Beat {i}: description too short (min 10 chars)")
        
        if "segment_enrichments" not in output:
            errors.append("Missing 'segment_enrichments' array")
        else:
            enrichments = output.get("segment_enrichments", [])
            valid_text_layer = ["show", "hide", "swap"]
            valid_visual_layer = ["show", "hide", "replace"]
            valid_avatar_layer = ["show", "gesture_only"]
            
            for i, enrich in enumerate(enrichments):
                if "segment_id" not in enrich:
                    errors.append(f"Enrichment {i}: missing 'segment_id'")
                
                if "visual_content" not in enrich:
                    errors.append(f"Enrichment {i}: missing 'visual_content'")
                
                if "display_directives" not in enrich:
                    errors.append(f"Enrichment {i}: missing 'display_directives'")
                else:
                    dd = enrich.get("display_directives", {})
                    if dd.get("text_layer") not in valid_text_layer:
                        errors.append(f"Enrichment {i}: invalid text_layer '{dd.get('text_layer')}'")
                    if dd.get("visual_layer") not in valid_visual_layer:
                        errors.append(f"Enrichment {i}: invalid visual_layer '{dd.get('visual_layer')}'")
                    if dd.get("avatar_layer") not in valid_avatar_layer:
                        errors.append(f"Enrichment {i}: invalid avatar_layer '{dd.get('avatar_layer')}' (must be 'show' or 'gesture_only')")
        
        return len(errors) == 0, errors
    
    def validate_semantic(self, output: Dict[str, Any], input_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate semantic rules for combined output."""
        errors = []
        
        blueprint = input_data.get("section_blueprint", {})
        section_type = blueprint.get("section_type", "content")
        
        narration = output.get("narration", {})
        full_text = narration.get("full_text", "")
        word_count = len(full_text.split())
        
        min_words, max_words = self.WORD_LIMITS.get(section_type, (50, 300))
        # Allow 10% tolerance on minimum word count (149 vs 150 should pass)
        min_with_tolerance = int(min_words * 0.9)
        if word_count < min_with_tolerance:
            errors.append(f"Narration too short for {section_type}: {word_count} words (min {min_words})")
        if word_count > max_words * 1.5:
            errors.append(f"Narration too long for {section_type}: {word_count} words (max ~{max_words})")
        
        segments = narration.get("segments", [])
        total_segment_words = sum(len(s.get("text", "").split()) for s in segments)
        if abs(total_segment_words - word_count) > 10:
            errors.append(f"Segment word count ({total_segment_words}) doesn't match full_text ({word_count})")
        
        min_segs, max_segs = self.SEGMENT_LIMITS.get(section_type, (2, 5))
        if len(segments) < min_segs or len(segments) > max_segs:
            errors.append(f"{section_type} section should have {min_segs}-{max_segs} segments, got {len(segments)}")
        
        segment_ids = {s.get("segment_id") for s in segments}
        
        beats = output.get("visual_beats", [])
        for beat in beats:
            if beat.get("segment_id") not in segment_ids:
                errors.append(f"Beat {beat.get('beat_id')}: segment_id {beat.get('segment_id')} not in narration")
        
        enrichments = output.get("segment_enrichments", [])
        enrichment_ids = {e.get("segment_id") for e in enrichments}
        
        for seg_id in segment_ids:
            if seg_id not in enrichment_ids:
                errors.append(f"Missing segment_enrichment for segment_id {seg_id}")
        
        for enrich in enrichments:
            dd = enrich.get("display_directives", {})
            if dd.get("text_layer") == "show" and dd.get("visual_layer") == "show":
                errors.append(f"Segment {enrich.get('segment_id')}: text_layer and visual_layer cannot both be 'show'")
            if dd.get("avatar_layer") == "hide":
                errors.append(f"Segment {enrich.get('segment_id')}: avatar_layer cannot be 'hide' (avatar always visible)")
        
        if len(beats) != len(segments):
            errors.append(f"Beat count ({len(beats)}) should match segment count ({len(segments)})")
        
        if section_type == "intro":
            if not any(word in full_text.lower() for word in ["namaste", "welcome", "hello", "greet"]):
                errors.append("Intro section should start with warm greeting (e.g., 'Namaste students')")
        
        return len(errors) == 0, errors
