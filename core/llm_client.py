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
