import os
import json
import re
from pathlib import Path
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

AI_INTEGRATIONS_OPENROUTER_API_KEY = os.environ.get("AI_INTEGRATIONS_OPENROUTER_API_KEY")
AI_INTEGRATIONS_OPENROUTER_BASE_URL = os.environ.get("AI_INTEGRATIONS_OPENROUTER_BASE_URL")

openrouter = OpenAI(
    api_key=AI_INTEGRATIONS_OPENROUTER_API_KEY,
    base_url=AI_INTEGRATIONS_OPENROUTER_BASE_URL
)

PROMPTS_DIR = Path(__file__).parent / "prompts"

def load_system_prompt() -> str:
    with open(PROMPTS_DIR / "system_prompt.txt", "r") as f:
        return f.read()

def load_user_prompt() -> str:
    with open(PROMPTS_DIR / "user_prompt.txt", "r") as f:
        return f.read()

def validate_and_fix_presentation(presentation: dict, subject: str, grade: str) -> dict:
    if "chapter_title" not in presentation:
        presentation["chapter_title"] = "Educational Content"
    if "subject" not in presentation:
        presentation["subject"] = subject
    if "grade" not in presentation:
        presentation["grade"] = grade
    if "language" not in presentation:
        presentation["language"] = "en-IN"
    if "topics" not in presentation:
        presentation["topics"] = []
    
    for i, topic in enumerate(presentation.get("topics", [])):
        if "id" not in topic:
            topic["id"] = i + 1
        if "title" not in topic:
            topic["title"] = f"Topic {topic['id']}"
        if "renderer" not in topic:
            topic["renderer"] = "wan_video"
        if "explanation_plan" not in topic:
            topic["explanation_plan"] = {"wan_prompt": f"Educational visualization for {topic['title']}"}
        if "duration" not in topic:
            topic["duration"] = 30
        if "layout" not in topic:
            topic["layout"] = {
                "content_zone": {"position": "left", "width_percent": 65},
                "avatar_zone": {"mode": "side", "position": "right", "width_percent": 35, "scale": 0.35}
            }
        if "narration" not in topic:
            topic["narration"] = f"This topic covers {topic['title']}."
        if "segments" not in topic or not topic["segments"]:
            narration = topic.get("narration", "")
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
            topic["segments"] = segments if segments else [{"start": 0.0, "duration": 3.0, "text": topic["narration"]}]
        if "gesture_hints" not in topic:
            topic["gesture_hints"] = [{"time": 1.0, "action": "explain"}]
    
    return presentation

def is_rate_limit_error(exception: BaseException) -> bool:
    error_msg = str(exception)
    return (
        "429" in error_msg
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower()
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, "status_code") and exception.status_code == 429)
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
        "topics_generated": len(presentation_json.get("topics", [])),
        "renderer_decisions": []
    }
    
    for topic in presentation_json.get("topics", []):
        renderer = topic.get("renderer", "unknown")
        reason = "math/geometry content" if renderer == "manim" else "conceptual/science content"
        generation_trace["renderer_decisions"].append({
            "topic_id": topic.get("id"),
            "topic_title": topic.get("title"),
            "renderer": renderer,
            "reason": reason,
            "prompt_used": topic.get("explanation_plan", {})
        })
    
    return presentation_json, generation_trace
