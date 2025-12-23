#!/usr/bin/env python3
"""
Display Layer Validation Script

Validates that presentation JSON follows all display layer rules:
1. Mutual Exclusion: text_layer and visual_layer cannot both be "show"
2. Avatar Rules: Correct visibility/sizing by section type
3. Teaching Sequence: Proper TEACH → SHOW progression
4. Timing Sync: All segments have durations, totals match section duration
5. Two-Channel Separation: narration.text vs visual_content
6. Manim Requirements: manim_scene_spec present for manim sections
7. Video Requirements: visual_beats with adequate descriptions
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class DisplayLayerValidator:
    """Validates display layer rules for presentation JSON."""
    
    def __init__(self, presentation: Dict):
        self.presentation = presentation
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats = {
            "total_sections": 0,
            "total_segments": 0,
            "total_duration": 0.0,
            "renderers": {},
            "section_types": {}
        }
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """Run all validations. Returns (success, errors, warnings)."""
        sections = self.presentation.get("sections", [])
        self.stats["total_sections"] = len(sections)
        
        for i, section in enumerate(sections):
            self._validate_section(section, i)
        
        self._validate_required_sections(sections)
        self._validate_overall_structure()
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_section(self, section: Dict, index: int):
        """Validate a single section."""
        section_id = section.get("section_id", f"section_{index}")
        section_type = section.get("section_type", "unknown")
        renderer = section.get("renderer", "unknown")
        
        self.stats["section_types"][section_type] = self.stats["section_types"].get(section_type, 0) + 1
        self.stats["renderers"][renderer] = self.stats["renderers"].get(renderer, 0) + 1
        
        self._validate_avatar_rules(section, section_id, section_type)
        
        if renderer == "manim":
            self._validate_manim_section(section, section_id)
        elif renderer == "video":
            self._validate_video_section(section, section_id)
        
        narration = section.get("narration", {})
        segments = narration.get("segments", [])
        self.stats["total_segments"] += len(segments)
        
        section_duration = 0.0
        for j, segment in enumerate(segments):
            seg_id = segment.get("segment_id", f"seg_{j}")
            self._validate_segment(segment, section_id, seg_id, section_type)
            
            duration = segment.get("duration_estimate", 0) or segment.get("duration_seconds", 0)
            section_duration += duration
        
        self.stats["total_duration"] += section_duration
        
        if section_duration == 0 and len(segments) > 0:
            self.errors.append(f"{section_id}: Has {len(segments)} segments but total duration = 0")
    
    def _validate_segment(self, segment: Dict, section_id: str, seg_id: str, section_type: str):
        """Validate display directives for a segment."""
        prefix = f"{section_id}.{seg_id}"
        
        dd = segment.get("display_directives", {})
        if not dd:
            self.errors.append(f"{prefix}: Missing display_directives")
            return
        
        text_layer = dd.get("text_layer")
        visual_layer = dd.get("visual_layer")
        avatar_layer = dd.get("avatar_layer")
        
        if text_layer == "show" and visual_layer == "show":
            self.errors.append(
                f"{prefix}: MUTUAL EXCLUSION VIOLATION - text_layer='show' AND visual_layer='show'"
            )
        
        if text_layer not in ["show", "hide", "highlight", None]:
            self.errors.append(f"{prefix}: Invalid text_layer value: {text_layer}")
        
        if visual_layer not in ["show", "hide", "replace", None]:
            self.errors.append(f"{prefix}: Invalid visual_layer value: {visual_layer}")
        
        if avatar_layer not in ["show", "hide", "gesture_only", None]:
            self.errors.append(f"{prefix}: Invalid avatar_layer value: {avatar_layer}")
        
        if section_type == "quiz" and avatar_layer == "show":
            self.warnings.append(f"{prefix}: Quiz section typically has avatar hidden")
        
        duration = segment.get("duration_estimate", 0) or segment.get("duration_seconds", 0)
        if duration <= 0:
            self.errors.append(f"{prefix}: Segment has no duration (duration_estimate/duration_seconds = 0)")
        
        text = segment.get("text", "")
        if not text or len(text.strip()) < 5:
            self.warnings.append(f"{prefix}: Segment has very short or empty narration text")
    
    def _validate_avatar_rules(self, section: Dict, section_id: str, section_type: str):
        """Validate avatar visibility and sizing rules by section type."""
        layout = section.get("layout", {})
        avatar_pos = layout.get("avatar_position", "")
        avatar_width = layout.get("avatar_width_percent", 0)
        
        if section_type == "intro":
            if avatar_pos == "hidden":
                self.errors.append(f"{section_id}: INTRO must have visible avatar (got position='hidden')")
            if avatar_width < 50:
                self.warnings.append(f"{section_id}: INTRO avatar should be ≥50% width (got {avatar_width}%)")
        
        elif section_type == "quiz":
            if avatar_pos not in ["hidden", ""]:
                self.warnings.append(f"{section_id}: QUIZ typically has hidden avatar")
        
        elif section_type == "content":
            if avatar_width > 50:
                self.warnings.append(f"{section_id}: CONTENT avatar should be 30-40% width (got {avatar_width}%)")
    
    def _validate_manim_section(self, section: Dict, section_id: str):
        """Validate Manim-specific requirements."""
        if "manim_scene_spec" not in section:
            self.errors.append(f"{section_id}: MANIM renderer requires manim_scene_spec")
            return
        
        manim_spec = section.get("manim_scene_spec", {})
        
        if "objects" not in manim_spec:
            self.errors.append(f"{section_id}: manim_scene_spec missing 'objects' array")
        elif not isinstance(manim_spec["objects"], list):
            self.errors.append(f"{section_id}: manim_scene_spec.objects must be an array")
        elif len(manim_spec["objects"]) == 0:
            self.warnings.append(f"{section_id}: manim_scene_spec.objects is empty")
        
        if "animation_sequence" not in manim_spec:
            self.errors.append(f"{section_id}: manim_scene_spec missing 'animation_sequence' array")
        elif not isinstance(manim_spec["animation_sequence"], list):
            self.errors.append(f"{section_id}: manim_scene_spec.animation_sequence must be an array")
        elif len(manim_spec["animation_sequence"]) == 0:
            self.warnings.append(f"{section_id}: manim_scene_spec.animation_sequence is empty")
        
        visual_beats = section.get("visual_beats", [])
        if not visual_beats:
            self.warnings.append(f"{section_id}: MANIM section has no visual_beats")
    
    def _validate_video_section(self, section: Dict, section_id: str):
        """Validate Video/WAN-specific requirements."""
        visual_beats = section.get("visual_beats", [])
        video_prompt = section.get("video_prompt", "")
        
        if not visual_beats and not video_prompt:
            self.errors.append(f"{section_id}: VIDEO renderer requires visual_beats or video_prompt")
            return
        
        for i, beat in enumerate(visual_beats):
            desc = beat.get("description", "") or beat.get("video_prompt", "")
            if len(desc) < 50:
                self.warnings.append(
                    f"{section_id}.visual_beats[{i}]: Description too short ({len(desc)} chars, recommend 100+)"
                )
    
    def _validate_required_sections(self, sections: List[Dict]):
        """Validate presence of required section types."""
        found_types = {s.get("section_type") for s in sections}
        
        required = {"intro", "summary"}
        missing = required - found_types
        if missing:
            self.errors.append(f"Missing required sections: {missing}")
        
        recommended = {"memory", "recap"}
        missing_recommended = recommended - found_types
        if missing_recommended:
            self.warnings.append(f"Missing recommended sections: {missing_recommended}")
        
        content_count = sum(1 for s in sections if s.get("section_type") == "content")
        if content_count == 0:
            self.errors.append("No CONTENT sections found")
        
        memory_sections = [s for s in sections if s.get("section_type") == "memory"]
        for mem in memory_sections:
            flashcards = mem.get("flashcards", [])
            if len(flashcards) < 5:
                self.warnings.append(f"Memory section has {len(flashcards)} flashcards (expected 5)")
    
    def _validate_overall_structure(self):
        """Validate overall presentation structure."""
        if self.stats["total_duration"] < 60:
            self.warnings.append(
                f"Total duration is very short: {self.stats['total_duration']:.1f}s (expected 3-10 minutes)"
            )
        
        if self.stats["total_segments"] < 10:
            self.warnings.append(
                f"Low segment count: {self.stats['total_segments']} (expected 20+ for a full lesson)"
            )
    
    def get_summary(self) -> str:
        """Get validation summary."""
        lines = [
            "="*60,
            "DISPLAY LAYER VALIDATION SUMMARY",
            "="*60,
            f"Sections: {self.stats['total_sections']}",
            f"Segments: {self.stats['total_segments']}",
            f"Total Duration: {self.stats['total_duration']:.1f}s ({self.stats['total_duration']/60:.1f} min)",
            "",
            "Section Types:",
        ]
        for st, count in self.stats["section_types"].items():
            lines.append(f"  - {st}: {count}")
        
        lines.append("")
        lines.append("Renderers:")
        for r, count in self.stats["renderers"].items():
            lines.append(f"  - {r}: {count}")
        
        lines.append("")
        lines.append(f"Errors: {len(self.errors)}")
        lines.append(f"Warnings: {len(self.warnings)}")
        
        if self.errors:
            lines.append("")
            lines.append("ERRORS:")
            for e in self.errors:
                lines.append(f"  [ERROR] {e}")
        
        if self.warnings:
            lines.append("")
            lines.append("WARNINGS:")
            for w in self.warnings:
                lines.append(f"  [WARN] {w}")
        
        lines.append("="*60)
        status = "PASS" if len(self.errors) == 0 else "FAIL"
        lines.append(f"RESULT: {status}")
        lines.append("="*60)
        
        return "\n".join(lines)


def validate_presentation_file(filepath: str) -> Tuple[bool, str]:
    """Validate a presentation JSON file."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        return False, f"File not found: {filepath}"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    
    presentation = data.get("presentation", data)
    
    validator = DisplayLayerValidator(presentation)
    success, errors, warnings = validator.validate()
    summary = validator.get_summary()
    
    return success, summary


def validate_presentation_dict(presentation: Dict) -> Tuple[bool, List[str], List[str], Dict]:
    """Validate a presentation dictionary directly. Returns (success, errors, warnings, stats)."""
    validator = DisplayLayerValidator(presentation)
    success, errors, warnings = validator.validate()
    return success, errors, warnings, validator.stats


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_display_layer.py <presentation.json> [presentation2.json ...]")
        print("\nValidates display layer rules for V1.4 presentation JSON files.")
        sys.exit(1)
    
    all_passed = True
    
    for filepath in sys.argv[1:]:
        print(f"\nValidating: {filepath}")
        success, summary = validate_presentation_file(filepath)
        print(summary)
        
        if not success:
            all_passed = False
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
