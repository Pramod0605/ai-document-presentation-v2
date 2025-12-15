import os
import json
import re
from pathlib import Path
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

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
    "impressive display"
]


class ValidationError(Exception):
    pass


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


def validate_visual_beat(beat: dict, section_id: int, beat_index: int) -> list:
    errors = []
    if "segment_id" not in beat or not isinstance(beat.get("segment_id"), (int, float)):
        errors.append(f"Section {section_id}: visual_beat[{beat_index}] missing or invalid 'segment_id' (must be numeric)")
    if "visual_instruction" not in beat or not isinstance(beat.get("visual_instruction"), str) or not beat.get("visual_instruction", "").strip():
        errors.append(f"Section {section_id}: visual_beat[{beat_index}] missing or empty 'visual_instruction'")
    if "labels" not in beat or not isinstance(beat.get("labels"), list):
        errors.append(f"Section {section_id}: visual_beat[{beat_index}] missing 'labels' array")
    if "motion" not in beat or not isinstance(beat.get("motion"), str):
        errors.append(f"Section {section_id}: visual_beat[{beat_index}] missing 'motion' description")
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
            beat_errors = validate_visual_beat(beat, section_id, i)
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
    
    for beat in visual_beats:
        instruction = beat.get("visual_instruction", "")
        vague = check_vague_phrases(instruction)
        if vague:
            msg = f"Section {section_id}: visual_beat contains banned vague phrases: {vague}"
            if is_critical:
                errors.append(msg)
            else:
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
    model: str = "meta-llama/llama-3.3-70b-instruct"
) -> tuple[dict, dict]:
    print("\n" + "="*60)
    print("LLM GENERATION - START")
    print("="*60)
    
    system_prompt = load_system_prompt()
    user_prompt_template = load_user_prompt()
    
    user_prompt = user_prompt_template.format(
        subject=subject,
        grade=grade,
        markdown_content=markdown_content
    )
    
    print(f"\n[MODEL]: {model}")
    print(f"[SYSTEM PROMPT]: {len(system_prompt)} chars, first 200: {system_prompt[:200]}...")
    print(f"[USER PROMPT]: {len(user_prompt)} chars")
    print(f"[INPUT MARKDOWN]: {len(markdown_content)} chars")
    print(f"[MAX TOKENS]: 8192")
    print(f"[TEMPERATURE]: 0.7")
    print("\n--- Calling OpenRouter API ---")
    
    response = openrouter.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=8192,
        temperature=0.7
    )
    
    response_text = response.choices[0].message.content or ""
    
    print(f"\n[RAW RESPONSE LENGTH]: {len(response_text)} chars")
    print(f"[RAW RESPONSE PREVIEW]: {response_text[:500]}...")
    
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        print(f"[JSON EXTRACTION]: Found JSON block of {len(json_match.group())} chars")
        presentation_json = json.loads(json_match.group())
    else:
        print("[JSON EXTRACTION]: FAILED - No JSON found!")
        raise ValueError("LLM did not return valid JSON")
    
    presentation_json, validation_errors, validation_warnings = validate_and_fix_presentation(
        presentation_json, subject, grade
    )
    
    print(f"\n[SECTIONS GENERATED]: {len(presentation_json.get('sections', []))}")
    print("\n--- Section-by-Section Analysis ---")
    for sec in presentation_json.get("sections", []):
        sec_id = sec.get("id", "?")
        sec_type = sec.get("section_type", "unknown")
        sec_title = sec.get("title", "Untitled")[:40]
        narr = sec.get("narration", "")
        wc = count_words(narr)
        has_segments = "YES" if sec.get("narration_segments") else "NO"
        has_beats = "YES" if sec.get("visual_beats") else "NO"
        status = "OK" if (sec_type != "content" or wc >= CONTENT_MIN_WORDS) else "FAIL"
        print(f"  [{sec_id}] {sec_type:8} | {wc:3} words | segments:{has_segments} beats:{has_beats} | {status} | {sec_title}")
    
    print(f"\n[VALIDATION ERRORS]: {len(validation_errors)}")
    for err in validation_errors:
        print(f"  ERROR: {err}")
    print(f"[VALIDATION WARNINGS]: {len(validation_warnings)}")
    for warn in validation_warnings:
        if isinstance(warn, ValidationWarning):
            print(f"  WARN: {warn.message}")
    
    print("\n" + "="*60)
    print("LLM GENERATION - END")
    print("="*60 + "\n")
    
    generation_trace = {
        "prompt_version": "v2",
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "model": model,
        "raw_response": response_text,
        "sections_generated": len(presentation_json.get("sections", [])),
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
        raise ValidationError(error_msg)
    
    return presentation_json, generation_trace
