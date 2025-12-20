"""
LLM Client v1.3 - Deterministic Educational Film Engine

Pipeline Phases:
- Pass 0: Chunker (Gemini 2.5 Flash) - Split markdown into clean chunks
- Pass 1: Director (Gemini 2.5 Pro) - Create pedagogy, structure, timing, display_directives
- Pass 2: Renderers - Deterministic rendering (NO creative LLM decisions):
    - Manim Renderer (Claude 3.5 Sonnet) - Math/physics code from manim_scene_spec
    - Remotion Renderer (Claude 3.5 Sonnet) - Motion graphics (when enabled)
    - Video Renderer (Gemini 2.5 Pro) - WAN prompts from visual_beats

v1.3 Key Changes:
- display_directives for every narration segment (text_layer, visual_layer, avatar_layer)
- Mandatory intro, summary, memory, recap sections (hard fail if missing)
- Avatar rules per section type (intro=center/large, content=side, recap=hidden)
- Manim sections MUST have manim_scene_spec - prose-only = HARD FAILURE
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from core.analytics import AnalyticsTracker, create_tracker
from core.traceability import save_raw_llm_response


def log(msg: str):
    print(msg)
    sys.stdout.flush()


OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL
)

PROMPTS_DIR = Path(__file__).parent / "prompts"

MODELS = {
    "chunker": "google/gemini-2.5-flash",
    "director": "google/gemini-2.5-pro",
    "manim_renderer": "anthropic/claude-3.5-sonnet",
    "remotion_renderer": "anthropic/claude-3.5-sonnet",
    "video_renderer": "google/gemini-2.5-pro"
}


class PipelineError(Exception):
    """Error raised when pipeline fails."""
    def __init__(self, message: str, phase: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.phase = phase
        self.details = details or {}


def load_prompt(name: str, version: str = "v1.3") -> str:
    """Load a prompt file. Falls back to v1.2 if v1.3 doesn't exist."""
    path = PROMPTS_DIR / f"{name}_{version}.txt"
    if not path.exists():
        fallback_path = PROMPTS_DIR / f"{name}_v1.2.txt"
        if fallback_path.exists():
            log(f"[Prompts] Using v1.2 fallback for {name}")
            path = fallback_path
        else:
            raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, "r") as f:
        return f.read()


def fix_json(text: str) -> str:
    """Clean up LLM JSON output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    
    return text


def parse_json_response(text: str, phase: str) -> Dict:
    """Parse JSON from LLM response with error handling."""
    try:
        fixed = fix_json(text)
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        log(f"[{phase}] JSON parse error: {e}")
        log(f"[{phase}] Raw text (first 500 chars): {text[:500]}")
        raise PipelineError(f"Failed to parse JSON from {phase}", phase, {"error": str(e)})


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def call_llm(
    model: str,
    system_prompt: str,
    user_prompt: str,
    phase: str,
    tracker: Optional[AnalyticsTracker] = None
) -> Tuple[str, Dict]:
    """Make an LLM call with retry and analytics tracking."""
    
    if tracker:
        tracker.start_phase(phase, model)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=16000
        )
        
        content = response.choices[0].message.content or ""
        usage = {
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0
        }
        
        if tracker:
            tracker.end_phase(phase, usage["input_tokens"], usage["output_tokens"])
        
        return content, usage
        
    except Exception as e:
        if tracker:
            tracker.end_phase(phase, 0, 0, status="failed", error=str(e))
        raise


def pass0_chunker(
    markdown_content: str,
    tracker: Optional[AnalyticsTracker] = None
) -> Dict:
    """Pass 0: Split markdown into teachable chunks."""
    log("[Parse] Starting Chunker...")
    
    system_prompt = load_prompt("chunker_system")
    user_template = load_prompt("chunker_user")
    user_prompt = user_template.replace("{markdown_content}", markdown_content)
    
    response_text, usage = call_llm(
        model=MODELS["chunker"],
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        phase="chunker",
        tracker=tracker
    )
    
    chunks = parse_json_response(response_text, "chunker")
    
    if "chunks" not in chunks:
        if isinstance(chunks, list):
            chunks = {"chunks": chunks}
        else:
            raise PipelineError("Chunker output missing 'chunks' array", "chunker")
    
    chunk_count = len(chunks.get("chunks", []))
    log(f"[Parse] Chunker complete: {chunk_count} chunks created")
    
    return chunks


def pass1_director(
    chunks: Dict,
    subject: str,
    grade: str,
    chapter: str = "",
    tracker: Optional[AnalyticsTracker] = None
) -> Dict:
    """Pass 1: Create pedagogy, structure, timing, renderer choices."""
    log("[Direct] Starting Director...")
    
    system_prompt = load_prompt("director_system")
    user_template = load_prompt("director_user")
    
    chunks_json = json.dumps(chunks, indent=2)
    
    user_prompt = user_template.replace("{subject}", subject)
    user_prompt = user_prompt.replace("{grade}", str(grade))
    user_prompt = user_prompt.replace("{chapter}", chapter or "Educational Content")
    user_prompt = user_prompt.replace("{chunks_json}", chunks_json)
    
    response_text, usage = call_llm(
        model=MODELS["director"],
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        phase="director",
        tracker=tracker
    )
    
    presentation = parse_json_response(response_text, "director")
    
    if "sections" not in presentation:
        if "lesson_plan" in presentation:
            log("[Direct] Converting 'lesson_plan' to 'sections' (LLM naming variation)")
            presentation["sections"] = presentation.pop("lesson_plan")
        elif "plan" in presentation:
            log("[Direct] Converting 'plan' to 'sections' (LLM naming variation)")
            presentation["sections"] = presentation.pop("plan")
        elif "topics" in presentation:
            log("[Direct] Converting 'topics' to 'sections' (LLM naming variation)")
            presentation["sections"] = presentation.pop("topics")
        else:
            log(f"[Direct] ERROR: Director returned keys: {list(presentation.keys())}")
            log(f"[Direct] ERROR: Response preview: {str(presentation)[:500]}")
            raise PipelineError("Director output missing 'sections' array", "director")
    
    section_count = len(presentation.get("sections", []))
    log(f"[Direct] Director complete: {section_count} sections created")
    
    RENDERER_FIELDS = ["manim_scene_spec", "remotion_scene_spec", "video_prompts", "wan_prompt"]
    stripped_count = 0
    renderer_counts = {}
    for section in presentation.get("sections", []):
        for rf in RENDERER_FIELDS:
            if rf in section:
                del section[rf]
                stripped_count += 1
        
        renderer = section.get("renderer", "unknown")
        if isinstance(renderer, dict):
            renderer = renderer.get("type", renderer.get("name", "unknown"))
            section["renderer"] = renderer
        renderer_counts[str(renderer)] = renderer_counts.get(str(renderer), 0) + 1
    
    if stripped_count > 0:
        log(f"[Direct] WARNING: Stripped {stripped_count} renderer fields from Director output (v1.2 violation)")
    log(f"[Direct] Renderer distribution: {renderer_counts}")
    
    return presentation


def pass2_manim_renderer(
    section: Dict,
    tracker: Optional[AnalyticsTracker] = None
) -> Dict:
    """Pass 2a: Generate manim_scene_spec for a section."""
    section_id = section.get("section_id") or section.get("id", 0)
    log(f"[Render:Manim] Section {section_id}...")
    
    system_prompt = load_prompt("manim_renderer_system")
    user_template = load_prompt("manim_renderer_user")
    
    section_json = json.dumps(section, indent=2)
    user_prompt = user_template.replace("{section_json}", section_json)
    
    response_text, usage = call_llm(
        model=MODELS["manim_renderer"],
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        phase=f"manim_renderer_s{section_id}",
        tracker=tracker
    )
    
    save_raw_llm_response(
        renderer_type="manim",
        section_id=str(section_id),
        raw_response=response_text,
        model=MODELS["manim_renderer"],
        usage=usage
    )
    
    result = parse_json_response(response_text, f"manim_renderer_s{section_id}")
    
    if "manim_scene_spec" not in result:
        raise PipelineError(
            f"Manim renderer failed to generate scene_spec for section {section_id}",
            "manim_renderer",
            {"section_id": section_id}
        )
    
    log(f"[Render:Manim] Scene spec generated for section {section_id}")
    return result


def pass2_remotion_renderer(
    section: Dict,
    tracker: Optional[AnalyticsTracker] = None
) -> Dict:
    """Pass 2b: Generate remotion_scene_spec for a section."""
    section_id = section.get("section_id") or section.get("id", 0)
    log(f"[Render:Remotion] Section {section_id}...")
    
    system_prompt = load_prompt("remotion_renderer_system")
    user_template = load_prompt("remotion_renderer_user")
    
    section_json = json.dumps(section, indent=2)
    user_prompt = user_template.replace("{section_json}", section_json)
    
    response_text, usage = call_llm(
        model=MODELS["remotion_renderer"],
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        phase=f"remotion_renderer_s{section_id}",
        tracker=tracker
    )
    
    save_raw_llm_response(
        renderer_type="remotion",
        section_id=str(section_id),
        raw_response=response_text,
        model=MODELS["remotion_renderer"],
        usage=usage
    )
    
    result = parse_json_response(response_text, f"remotion_renderer_s{section_id}")
    
    if "remotion_scene_spec" not in result:
        raise PipelineError(
            f"Remotion renderer failed to generate scene_spec for section {section_id}",
            "remotion_renderer",
            {"section_id": section_id}
        )
    
    log(f"[Render:Remotion] Scene spec generated for section {section_id}")
    return result


def pass2_video_renderer(
    section: Dict,
    tracker: Optional[AnalyticsTracker] = None
) -> Dict:
    """Pass 2c: Generate video prompts for a section."""
    section_id = section.get("section_id") or section.get("id", 0)
    log(f"[Render:Video] Section {section_id}...")
    
    system_prompt = load_prompt("video_renderer_system")
    user_template = load_prompt("video_renderer_user")
    
    section_json = json.dumps(section, indent=2)
    user_prompt = user_template.replace("{section_json}", section_json)
    
    response_text, usage = call_llm(
        model=MODELS["video_renderer"],
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        phase=f"video_renderer_s{section_id}",
        tracker=tracker
    )
    
    save_raw_llm_response(
        renderer_type="video",
        section_id=str(section_id),
        raw_response=response_text,
        model=MODELS["video_renderer"],
        usage=usage
    )
    
    result = parse_json_response(response_text, f"video_renderer_s{section_id}")
    
    log(f"[Render:Video] Prompts generated for section {section_id}")
    return result


def pass2_dispatch_renderers(
    presentation: Dict,
    tracker: Optional[AnalyticsTracker] = None,
    use_remotion: bool = True
) -> Dict:
    """Dispatch Render phase to appropriate renderers based on section renderer choice.
    
    v1.3 CHANGE: Director decides renderer. Pipeline obeys. No collapse logic.
    All sections (including intro/summary/memory) now have renderers assigned.
    
    Args:
        use_remotion: v1.3 defaults to True - Remotion is now a required renderer.
    """
    log("[Render v1.3] Dispatching to renderers (Director decides, pipeline obeys)...")
    
    sections = presentation.get("sections", [])
    
    for i, section in enumerate(sections):
        section_id = section.get("section_id") or section.get("id", i + 1)
        renderer = section.get("renderer", "")
        if isinstance(renderer, dict):
            renderer = renderer.get("type", renderer.get("name", ""))
        renderer = str(renderer).lower()
        section_type = section.get("section_type", "")
        
        log(f"[Render v1.3] Section {section_id} ({section_type}): renderer='{renderer}'")
        
        try:
            if renderer == "manim":
                result = pass2_manim_renderer(section, tracker)
                section["manim_scene_spec"] = result.get("manim_scene_spec")
                
            elif renderer == "remotion":
                result = pass2_remotion_renderer(section, tracker)
                section["remotion_scene_spec"] = result.get("remotion_scene_spec")
                
            elif renderer in ["video", "wan", "wan_video"]:
                result = pass2_video_renderer(section, tracker)
                if "video_prompts" in result:
                    section["video_prompts"] = result.get("video_prompts")
                elif "wan_prompt" in result:
                    section["video_prompts"] = [result]
                else:
                    section["video_prompts"] = result
                    
            else:
                log(f"[Render v1.3] WARN: Section {section_id} has unknown renderer '{renderer}'")
                
        except PipelineError as e:
            log(f"[Render v1.3] ERROR in section {section_id}: {e}")
            section["renderer_error"] = str(e)
    
    render_success = 0
    render_errors = 0
    for section in sections:
        section_id = section.get("section_id") or section.get("id", "?")
        renderer = str(section.get("renderer", "")).lower()
        
        if "renderer_error" in section:
            render_errors += 1
            continue
            
        if renderer == "manim" and not section.get("manim_scene_spec"):
            log(f"[Render v1.3] FAIL: Section {section_id} missing manim_scene_spec after render")
            section["renderer_error"] = "manim_scene_spec not generated"
            render_errors += 1
        elif renderer == "remotion" and not section.get("remotion_scene_spec"):
            log(f"[Render v1.3] FAIL: Section {section_id} missing remotion_scene_spec after render")
            section["renderer_error"] = "remotion_scene_spec not generated"
            render_errors += 1
        elif renderer in ["video", "wan", "wan_video"] and not section.get("video_prompts"):
            log(f"[Render v1.3] FAIL: Section {section_id} missing video_prompts after render")
            section["renderer_error"] = "video_prompts not generated"
            render_errors += 1
        else:
            render_success += 1
    
    log(f"[Render v1.3] Dispatch complete: {render_success} success, {render_errors} errors")
    return presentation


def generate_presentation_v12(
    markdown_content: str,
    subject: str = "General Science",
    grade: str = "9",
    chapter: str = "",
    use_remotion: bool = True
) -> Tuple[Dict, AnalyticsTracker]:
    """
    Main entry point for v1.3 3-phase pipeline (Parse → Direct → Render).
    
    v1.3 CHANGE: use_remotion defaults to True. Director decides renderer.
    
    Returns:
        Tuple of (presentation dict, analytics tracker)
    """
    import uuid
    job_id = str(uuid.uuid4())[:8]
    
    tracker = create_tracker(job_id)
    tracker.start_pipeline()
    
    try:
        chunks = pass0_chunker(markdown_content, tracker)
        
        presentation = pass1_director(chunks, subject, grade, chapter, tracker)
        
        presentation = pass2_dispatch_renderers(presentation, tracker, use_remotion=use_remotion)
        
        presentation["subject"] = subject
        presentation["grade"] = grade
        presentation["pipeline_version"] = "1.2"
        presentation["job_id"] = job_id
        
        tracker.end_pipeline(status="completed")
        tracker.print_summary()
        
        return presentation, tracker
        
    except Exception as e:
        tracker.end_pipeline(status="failed", error=str(e))
        tracker.print_summary()
        raise


def test_pipeline(markdown_path: str, subject: str = "General Science", grade: str = "9"):
    """Test the v1.2 pipeline with a markdown file."""
    log(f"\n{'='*60}")
    log("Testing v1.2 3-Pass Pipeline")
    log(f"{'='*60}")
    log(f"Input: {markdown_path}")
    log(f"Subject: {subject}, Grade: {grade}")
    log(f"{'='*60}\n")
    
    with open(markdown_path, "r") as f:
        content = f.read()
    
    presentation, tracker = generate_presentation_v12(content, subject, grade)
    
    output_path = Path(markdown_path).with_suffix(".presentation.json")
    with open(output_path, "w") as f:
        json.dump(presentation, f, indent=2)
    log(f"\nPresentation saved to: {output_path}")
    
    analytics_path = Path(markdown_path).with_suffix(".analytics.json")
    tracker.save_to_file(str(analytics_path))
    log(f"Analytics saved to: {analytics_path}")
    
    return presentation, tracker


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_pipeline(sys.argv[1])
    else:
        print("Usage: python llm_client_v12.py <markdown_file>")
