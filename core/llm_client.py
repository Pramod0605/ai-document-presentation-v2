import os
import sys
import json
import re
from pathlib import Path
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception


def log(msg: str):
    """Print with immediate flush for real-time logging."""
    print(msg)
    sys.stdout.flush()


_truncation_detected = False
_truncation_details = None

def was_truncated() -> tuple:
    """Return truncation status and details from last JSON fix."""
    global _truncation_detected, _truncation_details
    return _truncation_detected, _truncation_details

def fix_malformed_json(json_text: str) -> str:
    """Attempt to fix common JSON issues from LLM responses."""
    global _truncation_detected, _truncation_details
    _truncation_detected = False
    _truncation_details = None
    
    text = json_text.strip()
    
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    open_braces = text.count('{')
    close_braces = text.count('}')
    open_brackets = text.count('[')
    close_brackets = text.count(']')
    
    if open_braces > close_braces or open_brackets > close_brackets:
        _truncation_detected = True
        _truncation_details = {
            "open_braces": open_braces,
            "close_braces": close_braces,
            "open_brackets": open_brackets,
            "close_brackets": close_brackets,
            "original_length": len(json_text)
        }
        log(f"[TRUNCATION WARNING]: Response was TRUNCATED! Missing {open_braces - close_braces} braces and {open_brackets - close_brackets} brackets")
        log(f"[JSON FIX]: Detected truncated JSON - {open_braces} {{ vs {close_braces} }}, {open_brackets} [ vs {close_brackets} ]")
        
        search_patterns = [
            (r'\}\s*\]', '}]'),
            (r'\}\s*,', '},'),
            (r'"\s*\}', '"}'),
            (r'"\s*\]', '"]'),
            (r'\]\s*\}', ']}'),
            (r'\]\s*,', '],'),
        ]
        
        best_pos = -1
        for pattern, _ in search_patterns:
            matches = list(re.finditer(pattern, text))
            if matches:
                pos = matches[-1].end()
                if pos > best_pos and pos > len(text) // 2:
                    best_pos = pos
        
        if best_pos > 0:
            text = text[:best_pos]
            log(f"[JSON FIX]: Truncated to last complete structure at char {best_pos}")
        else:
            last_quote = text.rfind('"')
            if last_quote > len(text) // 2:
                search_back = text[:last_quote].rfind('"')
                if search_back > 0:
                    text = text[:last_quote + 1]
                    log(f"[JSON FIX]: Truncated to last complete string at char {last_quote}")
        
        text = re.sub(r',\s*$', '', text)
        
        open_braces = text.count('{')
        close_braces = text.count('}')
        open_brackets = text.count('[')
        close_brackets = text.count(']')
        
        closing_needed = []
        stack = []
        for char in text:
            if char == '{':
                stack.append('}')
            elif char == '[':
                stack.append(']')
            elif char in '}]':
                if stack and stack[-1] == char:
                    stack.pop()
        
        closing_needed = list(reversed(stack))
        
        if closing_needed:
            text = text.rstrip()
            if text.endswith(','):
                text = text[:-1]
            text += ''.join(closing_needed)
            log(f"[JSON FIX]: Added {len(closing_needed)} closing brackets: {''.join(closing_needed)}")
    
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    
    return text

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

openrouter = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL
)

PROMPTS_DIR = Path(__file__).parent / "prompts"

VALID_SECTION_TYPES = ["intro", "summary", "content", "example", "memory", "recap"]
CRITICAL_SECTION_TYPES = ["content", "example"]
CONTENT_MIN_WORDS = 150

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

VISUAL_INSTRUCTION_MIN_WORDS = 50


class ValidationError(Exception):
    def __init__(self, message: str, presentation=None, trace=None):
        super().__init__(message)
        self.presentation = presentation
        self.trace = trace


class ValidationWarning:
    def __init__(self, message: str, section_id: int, section_type: str):
        self.message = message
        self.section_id = section_id
        self.section_type = section_type


def load_system_prompt() -> str:
    with open(PROMPTS_DIR / "system_prompt.txt", "r") as f:
        return f.read()


def load_user_prompt() -> str:
    with open(PROMPTS_DIR / "user_prompt.txt", "r") as f:
        return f.read()


def count_words(text: str) -> int:
    return len(text.split()) if text else 0


def check_vague_phrases(text: str) -> list:
    found = []
    text_lower = text.lower()
    for phrase in BANNED_VAGUE_PHRASES:
        if phrase in text_lower:
            found.append(phrase)
    return found


def validate_narration_segment(segment: dict, section_id: int, segment_index: int) -> list:
    errors = []
    if "id" not in segment or not isinstance(segment.get("id"), (int, float)):
        errors.append(f"Section {section_id}: narration_segment[{segment_index}] missing or invalid 'id' (must be numeric)")
    if "text" not in segment or not isinstance(segment.get("text"), str) or not segment.get("text", "").strip():
        errors.append(f"Section {section_id}: narration_segment[{segment_index}] missing or empty 'text'")
    if "duration" not in segment or not isinstance(segment.get("duration"), (int, float)):
        errors.append(f"Section {section_id}: narration_segment[{segment_index}] missing or invalid 'duration' (must be numeric)")
    return errors


REQUIRED_VISUAL_BEAT_FIELDS = [
    "scene_setup",
    "objects_and_properties",
    "motion_sequence",
    "labels_and_text",
    "pedagogical_focus"
]

MIN_FIELD_WORDS = 8


def validate_visual_beat(beat: dict, section_id: int, beat_index: int, is_critical: bool = False) -> list:
    """Validate visual beat using 5-field structure (Gemini-safe)."""
    errors = []
    
    if "segment_id" not in beat or not isinstance(beat.get("segment_id"), (int, float)):
        errors.append(f"Section {section_id}: visual_beat[{beat_index}] missing or invalid 'segment_id' (must be numeric)")
    
    if is_critical:
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
                short_fields.append(f"{field}({word_count}w)")
            
            vague = check_vague_phrases(value)
            if vague:
                vague_fields.append(f"{field}")
        
        if missing_fields:
            errors.append(
                f"Section {section_id}: visual_beat[{beat_index}] missing required fields: {missing_fields}"
            )
        
        if short_fields:
            errors.append(
                f"Section {section_id}: visual_beat[{beat_index}] fields too short (need {MIN_FIELD_WORDS}+ words): {short_fields}"
            )
        
        if vague_fields:
            errors.append(
                f"Section {section_id}: visual_beat[{beat_index}] vague phrases in: {vague_fields}"
            )
    
    return errors


def validate_section_v2(section: dict) -> tuple[list, list]:
    errors = []
    warnings = []
    
    section_id = section.get("id", 0)
    section_type = section.get("section_type", "unknown")
    is_critical = section_type in CRITICAL_SECTION_TYPES
    renderer = section.get("renderer", "")
    
    narration = section.get("narration", "")
    word_count = count_words(narration)
    narration_segments = section.get("narration_segments", [])
    visual_beats = section.get("visual_beats", [])
    
    if section_type == "content":
        if word_count < CONTENT_MIN_WORDS:
            msg = f"Section {section_id} ({section_type}): narration has {word_count} words, minimum is {CONTENT_MIN_WORDS}"
            errors.append(msg)
        
        if not narration_segments:
            msg = f"Section {section_id} (content): missing narration_segments - required for V2"
            errors.append(msg)
        
        if narration_segments and not visual_beats:
            msg = f"Section {section_id} (content): has narration_segments but no visual_beats"
            errors.append(msg)
    
    if section_type == "example":
        if not narration_segments:
            msg = f"Section {section_id} (example): missing narration_segments for step-by-step explanation"
            errors.append(msg)
        if not visual_beats:
            msg = f"Section {section_id} (example): missing visual_beats - examples must be visualized"
            errors.append(msg)
        
        if renderer == "wan_video":
            title_lower = section.get("title", "").lower()
            is_biological = any(term in title_lower for term in ["biology", "cell", "organism", "plant", "animal", "enzyme", "protein"])
            if not is_biological:
                msg = f"Section {section_id} (example): renderer should be 'manim' for non-biological examples"
                errors.append(msg)
    
    if section_type in ["content", "example"]:
        for i, seg in enumerate(narration_segments):
            seg_errors = validate_narration_segment(seg, section_id, i)
            errors.extend(seg_errors)
        
        for i, beat in enumerate(visual_beats):
            beat_errors = validate_visual_beat(beat, section_id, i, is_critical=is_critical)
            errors.extend(beat_errors)
        
        if narration_segments and visual_beats:
            segment_ids = {s.get("id") for s in narration_segments if s.get("id") is not None}
            beat_segment_ids = {b.get("segment_id") for b in visual_beats if b.get("segment_id") is not None}
            missing_beats = segment_ids - beat_segment_ids
            if missing_beats:
                msg = f"Section {section_id} ({section_type}): narration segments {missing_beats} missing visual beats"
                errors.append(msg)
            
            if len(narration_segments) != len(visual_beats):
                msg = f"Section {section_id} ({section_type}): segment/beat count mismatch - {len(narration_segments)} segments vs {len(visual_beats)} beats"
                errors.append(msg)
    
    if not is_critical:
        for beat in visual_beats:
            instruction = beat.get("visual_instruction", "")
            vague = check_vague_phrases(instruction)
            if vague:
                msg = f"Section {section_id}: visual_beat contains banned vague phrases: {vague}"
                warnings.append(ValidationWarning(msg, section_id, section_type))
    
    wan_prompt = section.get("explanation_plan", {}).get("wan_prompt", "")
    if wan_prompt:
        vague = check_vague_phrases(wan_prompt)
        if vague:
            msg = f"Section {section_id}: wan_prompt contains banned vague phrases: {vague}"
            if is_critical:
                errors.append(msg)
            else:
                warnings.append(ValidationWarning(msg, section_id, section_type))
    
    return errors, warnings


def validate_presentation_structure(presentation: dict) -> tuple[list, list]:
    errors = []
    warnings = []
    
    sections = presentation.get("sections", [])
    section_types = [s.get("section_type") for s in sections]
    
    if "intro" not in section_types:
        warnings.append(ValidationWarning("Missing intro section", 0, "structure"))
    if "summary" not in section_types:
        warnings.append(ValidationWarning("Missing summary section", 0, "structure"))
    if "recap" not in section_types:
        warnings.append(ValidationWarning("Missing recap section", 0, "structure"))
    
    return errors, warnings


def validate_and_fix_presentation(presentation: dict, subject: str, grade: str) -> tuple[dict, list, list]:
    all_errors = []
    all_warnings = []
    
    if "chapter_title" not in presentation:
        presentation["chapter_title"] = "Educational Content"
    if "subject" not in presentation:
        presentation["subject"] = subject
    if "grade" not in presentation:
        presentation["grade"] = grade
    if "language" not in presentation:
        presentation["language"] = "en-IN"
    
    if "sections" not in presentation:
        if "topics" in presentation:
            presentation["sections"] = presentation.pop("topics")
        else:
            presentation["sections"] = []
    
    struct_errors, struct_warnings = validate_presentation_structure(presentation)
    all_errors.extend(struct_errors)
    all_warnings.extend(struct_warnings)
    
    for i, section in enumerate(presentation.get("sections", [])):
        if "id" not in section:
            section["id"] = i + 1
        if "title" not in section:
            section["title"] = f"Section {section['id']}"
        
        if "section_type" not in section:
            if i == 0:
                section["section_type"] = "intro"
            elif i == 1:
                section["section_type"] = "summary"
            elif i == len(presentation["sections"]) - 1:
                section["section_type"] = "recap"
            elif i == len(presentation["sections"]) - 2:
                section["section_type"] = "memory"
            else:
                section["section_type"] = "content"
        
        if section["section_type"] not in VALID_SECTION_TYPES:
            section["section_type"] = "content"
        
        if "renderer" not in section:
            if section["section_type"] == "example":
                section["renderer"] = "manim"
            else:
                section["renderer"] = "wan_video"
        
        if "explanation_plan" not in section:
            section["explanation_plan"] = {"wan_prompt": f"Educational visualization for {section['title']}"}
        
        if "visual_beats" in section and section["visual_beats"]:
            section["explanation_plan"]["visual_beats"] = section["visual_beats"]
        
        if "duration" not in section:
            section["duration"] = 30
        
        if "layout" not in section:
            if section["section_type"] in ["intro", "recap"]:
                section["layout"] = {
                    "content_zone": {"position": "center", "width_percent": 100},
                    "avatar_zone": {"mode": "overlay", "position": "bottom_center", "width_percent": 30}
                }
            elif section["section_type"] == "example":
                section["layout"] = {
                    "content_zone": {"position": "left", "width_percent": 70},
                    "avatar_zone": {"mode": "side", "position": "right", "width_percent": 30, "scale": 0.3}
                }
            else:
                section["layout"] = {
                    "content_zone": {"position": "left", "width_percent": 65},
                    "avatar_zone": {"mode": "side", "position": "right", "width_percent": 35, "scale": 0.35}
                }
        
        if "narration" not in section:
            section["narration"] = f"This section covers {section['title']}."
        
        if section["section_type"] == "memory" and "flashcards" not in section:
            section["flashcards"] = [
                {"question": "Key concept 1?", "answer": "Answer 1"},
                {"question": "Key concept 2?", "answer": "Answer 2"},
                {"question": "Key concept 3?", "answer": "Answer 3"}
            ]
        
        if section["section_type"] == "recap" and "recap_scenes" not in section:
            section["recap_scenes"] = [
                {"scene": 1, "description": "Opening scene"},
                {"scene": 2, "description": "Development"},
                {"scene": 3, "description": "Key moment"},
                {"scene": 4, "description": "Resolution"},
                {"scene": 5, "description": "Conclusion"}
            ]
        
        if "narration_segments" in section and section["narration_segments"]:
            section["segments"] = []
            current_time = 0.0
            for ns in section["narration_segments"]:
                duration = ns.get("duration", 4)
                section["segments"].append({
                    "start": round(current_time, 1),
                    "duration": round(duration, 1),
                    "text": ns.get("text", "")
                })
                current_time += duration
        elif "segments" not in section or not section["segments"]:
            narration = section.get("narration", "")
            words = narration.split()
            segment_size = max(10, len(words) // 3)
            segments = []
            start = 0.0
            for j in range(0, len(words), segment_size):
                segment_words = words[j:j+segment_size]
                text = " ".join(segment_words)
                duration = max(2.0, len(segment_words) * 0.3)
                segments.append({"start": round(start, 1), "duration": round(duration, 1), "text": text})
                start += duration
            section["segments"] = segments if segments else [{"start": 0.0, "duration": 3.0, "text": section["narration"]}]
        
        if "gesture_hints" not in section:
            section["gesture_hints"] = [{"time": 1.0, "action": "explain"}]
        
        if section["section_type"] in ["content", "example"]:
            narration_segments = section.get("narration_segments", [])
            visual_beats = section.get("visual_beats", [])
            
            if "visual_beats" not in section:
                section["visual_beats"] = []
            
            valid_beats = []
            for beat in visual_beats:
                is_valid = (
                    isinstance(beat.get("segment_id"), (int, float)) and
                    isinstance(beat.get("visual_instruction"), str) and
                    beat.get("visual_instruction", "").strip() and
                    isinstance(beat.get("labels"), list) and
                    isinstance(beat.get("motion"), str)
                )
                if is_valid:
                    valid_beats.append(beat)
                else:
                    log(f"[AUTO-REPAIR]: Removed incomplete visual_beat from section {section.get('id')}")
            
            section["visual_beats"] = valid_beats
            visual_beats = valid_beats
            
            if narration_segments:
                segment_ids = {s.get("id") for s in narration_segments if s.get("id") is not None}
                beat_segment_ids = {b.get("segment_id") for b in visual_beats if b.get("segment_id") is not None}
                missing_ids = segment_ids - beat_segment_ids
                
                for seg_id in sorted(missing_ids):
                    matching_seg = next((s for s in narration_segments if s.get("id") == seg_id), None)
                    seg_text = matching_seg.get("text", "Content explanation") if matching_seg else "Content explanation"
                    placeholder_beat = {
                        "segment_id": seg_id,
                        "visual_instruction": f"Display educational content related to: {seg_text[:100]}",
                        "labels": ["Educational content"],
                        "motion": "Static display with text overlay"
                    }
                    section["visual_beats"].append(placeholder_beat)
                    log(f"[AUTO-REPAIR]: Added placeholder visual_beat for segment {seg_id} in section {section.get('id')}")
        
        section_errors, section_warnings = validate_section_v2(section)
        all_errors.extend(section_errors)
        all_warnings.extend(section_warnings)
    
    return presentation, all_errors, all_warnings


def is_rate_limit_error(exception: BaseException) -> bool:
    error_msg = str(exception)
    return (
        "429" in error_msg
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower()
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, "status_code") and getattr(exception, "status_code", None) == 429)
    )


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True
)
def generate_presentation_plan(
    markdown_content: str,
    subject: str,
    grade: str,
    model: str = "google/gemini-2.5-flash"
) -> tuple[dict, dict]:
    log("\n" + "="*60)
    log("LLM GENERATION - START")
    log("="*60)
    
    system_prompt = load_system_prompt()
    user_prompt_template = load_user_prompt()
    
    user_prompt = user_prompt_template.format(
        subject=subject,
        grade=grade,
        markdown_content=markdown_content
    )
    
    log(f"\n[MODEL]: {model}")
    log(f"[SYSTEM PROMPT]: {len(system_prompt)} chars, first 200: {system_prompt[:200]}...")
    log(f"[USER PROMPT]: {len(user_prompt)} chars")
    log(f"[INPUT MARKDOWN]: {len(markdown_content)} chars")
    log(f"[MAX TOKENS]: 65536")
    log(f"[TEMPERATURE]: 0.7")
    log("\n--- Calling OpenRouter API ---")
    
    response = openrouter.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=65536,
        temperature=0.7
    )
    
    response_text = response.choices[0].message.content or ""
    
    log(f"\n[RAW RESPONSE LENGTH]: {len(response_text)} chars")
    log(f"[RAW RESPONSE PREVIEW]: {response_text[:500]}...")
    
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        json_text = json_match.group()
        log(f"[JSON EXTRACTION]: Found JSON block of {len(json_text)} chars")
        
        try:
            presentation_json = json.loads(json_text)
        except json.JSONDecodeError as e:
            log(f"[JSON ERROR]: {e}")
            log(f"[JSON ERROR]: Attempting to fix malformed JSON...")
            
            json_text = fix_malformed_json(json_text)
            try:
                presentation_json = json.loads(json_text)
                log(f"[JSON FIXED]: Successfully parsed after repair")
            except json.JSONDecodeError as e2:
                log(f"[JSON REPAIR FAILED]: {e2}")
                log(f"[JSON TAIL 500 chars]: ...{json_text[-500:]}")
                raise ValueError(f"LLM returned invalid JSON: {e2}")
    else:
        log("[JSON EXTRACTION]: FAILED - No JSON found!")
        raise ValueError("LLM did not return valid JSON")
    
    presentation_json, validation_errors, validation_warnings = validate_and_fix_presentation(
        presentation_json, subject, grade
    )
    
    log(f"\n[SECTIONS GENERATED]: {len(presentation_json.get('sections', []))}")
    log("\n--- Section-by-Section Analysis ---")
    for sec in presentation_json.get("sections", []):
        sec_id = sec.get("id", "?")
        sec_type = sec.get("section_type", "unknown")
        sec_title = sec.get("title", "Untitled")[:40]
        narr = sec.get("narration", "")
        wc = count_words(narr)
        has_segments = "YES" if sec.get("narration_segments") else "NO"
        has_beats = "YES" if sec.get("visual_beats") else "NO"
        status = "OK" if (sec_type != "content" or wc >= CONTENT_MIN_WORDS) else "FAIL"
        log(f"  [{sec_id}] {sec_type:8} | {wc:3} words | segments:{has_segments} beats:{has_beats} | {status} | {sec_title}")
    
    log(f"\n[VALIDATION ERRORS]: {len(validation_errors)}")
    for err in validation_errors:
        log(f"  ERROR: {err}")
    log(f"[VALIDATION WARNINGS]: {len(validation_warnings)}")
    for warn in validation_warnings:
        if isinstance(warn, ValidationWarning):
            log(f"  WARN: {warn.message}")
    
    log("\n" + "="*60)
    log("LLM GENERATION - END")
    log("="*60 + "\n")
    
    truncated, truncation_info = was_truncated()
    if truncated:
        log(f"[CRITICAL]: Response was truncated! This may cause incomplete visual beats in later sections.")
        log(f"[TRUNCATION DETAILS]: {truncation_info}")
        
        truncation_trace = {
            "prompt_version": "v2",
            "model": model,
            "max_tokens": 32768,
            "raw_response_length": len(response_text),
            "truncation": {
                "detected": True,
                "details": truncation_info
            },
            "fatal_error": "LLM response was truncated. Later sections may have incomplete content."
        }
        raise ValidationError(
            f"LLM response was TRUNCATED (missing {truncation_info.get('open_braces', 0) - truncation_info.get('close_braces', 0)} braces, "
            f"{truncation_info.get('open_brackets', 0) - truncation_info.get('close_brackets', 0)} brackets). "
            f"Response length: {len(response_text)} chars. Consider reducing input size or increasing max_tokens.",
            presentation_json,
            truncation_trace
        )
    
    generation_trace = {
        "prompt_version": "v2",
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "model": model,
        "max_tokens": 32768,
        "raw_response_length": len(response_text),
        "raw_response": response_text,
        "sections_generated": len(presentation_json.get("sections", [])),
        "truncation": {
            "detected": truncated,
            "details": truncation_info
        },
        "validation": {
            "errors": validation_errors,
            "warnings": [{"message": w.message, "section_id": w.section_id, "section_type": w.section_type} 
                        for w in validation_warnings if isinstance(w, ValidationWarning)],
            "passed": len(validation_errors) == 0
        },
        "section_decisions": [],
        "visual_beats_audit": []
    }
    
    content_sections = 0
    content_meeting_req = 0
    content_below_req = 0
    
    for section in presentation_json.get("sections", []):
        section_type = section.get("section_type", "content")
        renderer = section.get("renderer", "unknown")
        narration = section.get("narration", "")
        word_count = count_words(narration)
        visual_beats = section.get("visual_beats", [])
        
        meets_requirement = True
        if section_type == "content":
            content_sections += 1
            meets_requirement = word_count >= CONTENT_MIN_WORDS
            if meets_requirement:
                content_meeting_req += 1
            else:
                content_below_req += 1
        
        reason = "math/geometry content" if renderer == "manim" else "conceptual/science content"
        
        wan_prompt = section.get("explanation_plan", {}).get("wan_prompt", "")
        manim_plan = section.get("explanation_plan", {}).get("manim_plan", {})
        
        generation_trace["section_decisions"].append({
            "section_id": section.get("id"),
            "title": section.get("title"),
            "section_type": section_type,
            "renderer_decision": {
                "chosen": renderer,
                "reason": reason
            },
            "narration_stats": {
                "word_count": word_count,
                "meets_requirement": meets_requirement,
                "min_required": CONTENT_MIN_WORDS if section_type in ["content", "example"] else 0
            },
            "visual_beats_count": len(visual_beats),
            "prompts_used": {
                "wan_prompt": wan_prompt if renderer == "wan_video" else None,
                "manim_plan": manim_plan if renderer == "manim" else None
            },
            "pedagogy_notes": f"Section type: {section_type}"
        })
        
        if visual_beats:
            generation_trace["visual_beats_audit"].append({
                "section_id": section.get("id"),
                "section_type": section_type,
                "renderer": renderer,
                "beats": visual_beats
            })
    
    generation_trace["narration_validation"] = {
        "total_sections": len(presentation_json.get("sections", [])),
        "content_sections": content_sections,
        "content_meeting_requirement": content_meeting_req,
        "content_below_requirement": content_below_req
    }
    
    if validation_errors:
        error_msg = f"Validation failed with {len(validation_errors)} critical errors:\n" + "\n".join(validation_errors)
        generation_trace["validation"]["fatal_error"] = error_msg
        raise ValidationError(error_msg, presentation_json, generation_trace)
    
    return presentation_json, generation_trace
