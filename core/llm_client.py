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

VALID_SECTION_TYPES = ["intro", "summary", "content", "memory", "recap"]
CONTENT_MIN_WORDS = 150

def load_system_prompt() -> str:
    with open(PROMPTS_DIR / "system_prompt.txt", "r") as f:
        return f.read()

def load_user_prompt() -> str:
    with open(PROMPTS_DIR / "user_prompt.txt", "r") as f:
        return f.read()

def count_words(text: str) -> int:
    return len(text.split()) if text else 0

def validate_and_fix_presentation(presentation: dict, subject: str, grade: str) -> dict:
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
            section["renderer"] = "wan_video"
        if "explanation_plan" not in section:
            section["explanation_plan"] = {"wan_prompt": f"Educational visualization for {section['title']}"}
        if "duration" not in section:
            section["duration"] = 30
        if "layout" not in section:
            if section["section_type"] in ["intro", "recap"]:
                section["layout"] = {
                    "content_zone": {"position": "center", "width_percent": 100},
                    "avatar_zone": {"mode": "overlay", "position": "bottom_center", "width_percent": 30}
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
        
        if "segments" not in section or not section["segments"]:
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
    
    return presentation

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
    system_prompt = load_system_prompt()
    user_prompt_template = load_user_prompt()
    
    user_prompt = user_prompt_template.format(
        subject=subject,
        grade=grade,
        markdown_content=markdown_content
    )
    
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
    
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        presentation_json = json.loads(json_match.group())
    else:
        raise ValueError("LLM did not return valid JSON")
    
    presentation_json = validate_and_fix_presentation(presentation_json, subject, grade)
    
    generation_trace = {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "model": model,
        "raw_response": response_text,
        "sections_generated": len(presentation_json.get("sections", [])),
        "section_decisions": [],
        "narration_validation": {
            "total_sections": 0,
            "content_sections": 0,
            "content_meeting_requirement": 0,
            "content_below_requirement": 0
        }
    }
    
    content_sections = 0
    content_meeting_req = 0
    content_below_req = 0
    
    for section in presentation_json.get("sections", []):
        section_type = section.get("section_type", "content")
        renderer = section.get("renderer", "unknown")
        narration = section.get("narration", "")
        word_count = count_words(narration)
        
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
                "min_required": CONTENT_MIN_WORDS if section_type == "content" else 0
            },
            "prompts_used": {
                "wan_prompt": wan_prompt if renderer == "wan_video" else None,
                "manim_plan": manim_plan if renderer == "manim" else None
            },
            "pedagogy_notes": f"Section type: {section_type}"
        })
    
    generation_trace["narration_validation"]["total_sections"] = len(presentation_json.get("sections", []))
    generation_trace["narration_validation"]["content_sections"] = content_sections
    generation_trace["narration_validation"]["content_meeting_requirement"] = content_meeting_req
    generation_trace["narration_validation"]["content_below_requirement"] = content_below_req
    
    return presentation_json, generation_trace
