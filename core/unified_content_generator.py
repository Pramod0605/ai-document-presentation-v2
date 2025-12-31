"""
V2 Unified Content Generator

Single LLM call to generate complete presentation from raw markdown.
Includes retry wrapper for production resilience.
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass
class GeneratorConfig:
    """Configuration for the unified content generator."""
    model: str = "google/gemini-2.5-pro-preview"
    temperature: float = 0.7
    max_tokens: int = 32000
    max_retries: int = 3
    retry_delay_base: float = 2.0
    timeout: int = 300


class SchemaValidationError(Exception):
    """Raised when output doesn't match expected schema."""
    pass


class JSONParseError(Exception):
    """Raised when LLM response isn't valid JSON."""
    pass


UNIFIED_SYSTEM_PROMPT = """You are an expert Educational Video Script Generator for Indian students (Grade 8-12).

Your task: Convert a textbook chapter into a COMPLETE presentation JSON in a SINGLE response.

## SECTION TYPES (Generate in this order)
1. **intro** - Welcome message, AVATAR-ONLY narration (NO text/visuals on screen)
   - text_layer: "hide", visual_layer: "hide", avatar_layer: "show"
   - Just the teacher avatar speaking to camera
2. **summary** - Learning objectives as BULLET POINTS with narration (synced)
   - visual_type: "bullet_list" always
   - text_layer: "show", visual_layer: "show"
3. **content** - Main teaching content (2-5 sections based on document length)
   - LLM decides when to show text vs image vs diagram
   - Flip text_layer to "hide" when showing complex visuals
   - For BIOLOGY: Use derived_renderer="video" with video_prompts for anatomy, processes, organisms
   - For MATH/PHYSICS: Use derived_renderer="manim" for equations, graphs, formulas
4. **example** - OPTIONAL: Worked examples ONLY if present in source document
5. **quiz** - OPTIONAL: Questions extracted from document Q&A pairs (only if Q&A exists)
   - Split into multiple sections if >8 questions (~4 Q&A per section)
6. **memory** - Flashcard-style key concept review (1 section, 3-5 cards)
7. **recap** - EXACTLY 5 video scenes with story narration
   - MUST have exactly 5 segments and 5 video_prompts
   - text_layer: "hide", visual_layer: "show" (video takes full screen)
   - derived_renderer: "video"

## RENDERER SELECTION (Subject-Based) - APPLIES TO CONTENT SECTIONS
DEFAULT: "none" - For text, bullets, definitions, concepts

Subject-specific rules for CONTENT sections:
| Subject          | Content with visuals needs           | Example topics needing video/manim |
|------------------|--------------------------------------|-------------------------------------|
| Biology          | derived_renderer="video"             | Nervous System, Cells, Brain, Hormones |
| Mathematics      | derived_renderer="manim"             | Equations, Graphs, Geometry         |
| Physics          | derived_renderer="manim" or "video"  | Formulas (manim), Phenomena (video) |
| Chemistry        | derived_renderer="video" or "manim"  | Reactions (video), Equations (manim)|
| Other subjects   | derived_renderer="none"              | Text-only display                   |

WHEN TO USE VIDEO FOR BIOLOGY CONTENT:
- Anatomy topics (Nervous System, Brain, Heart) → video_prompts showing the structure
- Process topics (Reflex Arc, Photosynthesis) → video_prompts showing the process in action
- Organism topics (Cells, Hormones) → video_prompts showing microscopic views

RECAP SECTION: ALWAYS use "video" (WAN AI-generated scenes)

IMPORTANT: For Biology/Chemistry, most CONTENT sections with visual concepts should use derived_renderer="video" with video_prompts array.

## SEGMENT RULES
- Each segment = 15-30 seconds when spoken aloud
- Narration EXPLAINS, visuals REINFORCE (never duplicate)
- Avatar is ALWAYS visible: avatar_layer = "show"

## VISUAL BEAT TYPES (display_text = PDF TEXT, NOT narration)
CRITICAL: display_text MUST contain the ORIGINAL PDF text to show on screen.
         Narration (segment.text) is for AUDIO only - spoken by avatar.
         These are TWO SEPARATE THINGS:
         - display_text = What appears ON SCREEN (from PDF)
         - segment.text = What avatar SPEAKS (rewritten for natural speech)

- "text" - display_text = exact quote or paraphrase from PDF
- "bullet_list" - display_text = bullet items from PDF, NOT empty
- "equation" - latex_content = LaTeX formula from PDF
- "diagram" - display_text = diagram description, image_id = PDF image reference
- "image" - image_id = MUST reference actual PDF image ID (e.g., "abc123_img.jpg")
- "video" - AI-generated video (recap only)

## IMAGE USAGE RULE
You MUST use ALL images from the provided images_list. Every image in the PDF must appear in a visual_beat with:
  - visual_type: "image" or "diagram"
  - image_id: the exact image filename from the list

## QUIZ HANDLING
- Extract Q&A pairs from document's exercise/question sections
- Format as structured quiz with question, options, correct_answer, explanation
- Split into multiple quiz sections if >8 questions

## CRITICAL RULES
1. Include ALL content from source document - never summarize or skip
2. Preserve all educational details, definitions, examples
3. Maintain academic accuracy
4. Output MUST be valid JSON matching schema exactly
5. Every segment must have display_directives with avatar_layer: "show"

## OUTPUT SCHEMA
Return a JSON object with this exact structure:
{
  "presentation_title": "Chapter/Topic Name",
  "sections": [
    {
      "section_id": "section_1",
      "section_type": "intro|summary|content|example|quiz|memory|recap",
      "title": "Section Title",
      "derived_renderer": "none|manim|video",
      "narration": {
        "full_text": "Complete narration text for this section...",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "Individual segment narration...",
            "purpose": "introduce|explain|emphasize|transition|conclude",
            "display_directives": {
              "text_layer": "show|dim|hide",
              "visual_layer": "show|hide",
              "avatar_layer": "show"
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "text|bullet_list|equation|diagram|image|video",
          "display_text": "Visual content to show...",
          "latex_content": null,
          "image_id": null
        }
      ],
      "quiz_data": null,
      "flashcards": null,
      "video_prompts": null
    }
  ]
}

## SPECIAL SECTION DATA

For quiz sections, include:
"quiz_data": {
  "questions": [
    {
      "question": "Question text?",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_answer": "A",
      "explanation": "Why this is correct..."
    }
  ]
}

For memory sections, include:
"flashcards": [
  {
    "front": "Term or concept",
    "back": "Definition or explanation"
  }
]

For recap sections, include:
"video_prompts": [
  {
    "segment_id": "seg_1",
    "prompt": "Detailed video generation prompt...",
    "duration_hint": 10
  }
]

Return ONLY valid JSON, no markdown formatting or explanation."""


def build_user_prompt(
    markdown_content: str,
    subject: str = "Science",
    grade: str = "Grade 10",
    images_list: str = "None"
) -> str:
    """Build the user prompt with document content."""
    return f"""## Document Details
Subject: {subject}
Grade Level: {grade}
Available Images: {images_list}

## Source Document (Markdown)
```markdown
{markdown_content}
```

Generate the complete presentation JSON following the schema exactly. Include all section types in order: intro, summary, content, example (if applicable), quiz, memory, recap."""


def call_openrouter_llm(
    system_prompt: str,
    user_prompt: str,
    config: GeneratorConfig
) -> str:
    """Call OpenRouter API and return raw response text."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://replit.com",
        "X-Title": "AI Education V2"
    }
    
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens
    }
    
    response = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=config.timeout
    )
    response.raise_for_status()
    
    data = response.json()
    return data["choices"][0]["message"]["content"]


def extract_json_from_response(response: str) -> dict:
    """Extract and parse JSON from LLM response."""
    content = response.strip()
    
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    
    if content.endswith("```"):
        content = content[:-3]
    
    content = content.strip()
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise JSONParseError(f"Failed to parse JSON: {e}")


def normalize_output(output: dict) -> dict:
    """Normalize field names to expected schema."""
    if "title" in output and "presentation_title" not in output:
        output["presentation_title"] = output.pop("title")
    
    if "presentation" in output and "sections" not in output:
        output["sections"] = output.pop("presentation")
    
    return output


def validate_schema(output: dict) -> Tuple[bool, List[str]]:
    """Validate output against required schema. Returns (is_valid, errors)."""
    errors = []
    
    output = normalize_output(output)
    
    if "sections" not in output:
        errors.append("Missing 'sections' array")
        return False, errors
    
    sections = output.get("sections", [])
    if not sections:
        errors.append("Empty sections array")
        return False, errors
    
    required_section_fields = ["section_type", "narration"]
    
    for i, section in enumerate(sections):
        section_id = section.get("section_id", f"section_{i+1}")
        
        for field in required_section_fields:
            if field not in section:
                errors.append(f"[{section_id}] Missing required field: {field}")
        
        narration = section.get("narration", {})
        if "segments" not in narration:
            errors.append(f"[{section_id}] Missing narration.segments")
        elif not narration.get("segments"):
            errors.append(f"[{section_id}] Empty segments array")
        else:
            for j, seg in enumerate(narration["segments"]):
                if "text" not in seg:
                    errors.append(f"[{section_id}] Segment {j} missing 'text'")
                if "display_directives" not in seg:
                    errors.append(f"[{section_id}] Segment {j} missing 'display_directives'")
        
        if "visual_beats" not in section:
            errors.append(f"[{section_id}] Missing visual_beats")
    
    return len(errors) == 0, errors


def generate_presentation(
    markdown_content: str,
    subject: str = "Science",
    grade: str = "Grade 10",
    images_list: str = "None",
    config: Optional[GeneratorConfig] = None
) -> dict:
    """
    Generate complete presentation from raw markdown with retry.
    
    Args:
        markdown_content: Raw markdown from Datalab (no cleaning needed)
        subject: Subject area (e.g., "Biology", "Physics")
        grade: Grade level (e.g., "Grade 10")
        images_list: Comma-separated list of image IDs
        config: Generator configuration (uses defaults if None)
    
    Returns:
        Complete presentation dict ready for player transformation
    
    Raises:
        JSONParseError: If JSON parsing fails after all retries
        SchemaValidationError: If schema validation fails after all retries
        requests.RequestException: If API call fails after all retries
    """
    if config is None:
        config = GeneratorConfig()
    
    user_prompt = build_user_prompt(
        markdown_content=markdown_content,
        subject=subject,
        grade=grade,
        images_list=images_list
    )
    
    last_error = None
    
    for attempt in range(config.max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{config.max_retries}: Calling LLM...")
            
            response = call_openrouter_llm(
                system_prompt=UNIFIED_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                config=config
            )
            
            logger.info(f"Response received: {len(response)} chars")
            
            output = extract_json_from_response(response)
            logger.info("JSON parsed successfully")
            
            output = normalize_output(output)
            
            is_valid, errors = validate_schema(output)
            
            if not is_valid:
                raise SchemaValidationError(f"Schema validation failed: {errors[:3]}")
            
            logger.info("Schema validation passed")
            return output
            
        except (JSONParseError, SchemaValidationError) as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            
            if attempt < config.max_retries - 1:
                delay = config.retry_delay_base * (2 ** attempt)
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
            
        except requests.RequestException as e:
            last_error = e
            logger.warning(f"API error on attempt {attempt + 1}: {e}")
            
            if attempt < config.max_retries - 1:
                delay = config.retry_delay_base * (2 ** attempt)
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
    
    if last_error is not None:
        raise last_error
    raise RuntimeError("Generation failed after all retries")


def transform_to_player_schema(
    v2_output: dict,
    subject: str = "Science",
    grade: str = "10"
) -> dict:
    """
    Transform V2 output to final presentation.json format compatible with the player.
    
    Adds fields that are generated by post-processing (TTS, Manim, etc.)
    or have fixed values.
    """
    v2_output = normalize_output(v2_output)
    
    presentation = {
        "spec_version": "v1.5",
        "title": v2_output.get("presentation_title", "Lesson"),
        "subject": subject,
        "grade": grade,
        "avatar_global": {
            "style": "teacher",
            "default_position": "right",
            "default_width_percent": 52,
            "gesture_enabled": True
        },
        "metadata": {
            "generated_by": "v1.5-v2-unified",
            "llm_calls": 1
        },
        "sections": []
    }
    
    for i, section in enumerate(v2_output.get("sections", [])):
        transformed = {
            "section_id": i + 1,
            "section_type": section.get("section_type", "content"),
            "title": section.get("title", f"Section {i+1}"),
            "renderer": section.get("derived_renderer", "none"),
            "avatar_layout": {
                "visibility": "always",
                "mode": "floating",
                "position": "right" if section.get("section_type") != "intro" else "center",
                "width_percent": 52 if section.get("section_type") != "intro" else 60
            },
            "narration": _transform_narration(section.get("narration", {}), section.get("visual_beats", [])),
            "visual_beats": _transform_visual_beats(section.get("visual_beats", [])),
            "display_directives": _extract_display_directives(section),
        }
        
        if section.get("video_prompts"):
            transformed["video_prompts"] = section["video_prompts"]
        
        if section.get("quiz_data"):
            transformed["quiz_data"] = section["quiz_data"]
        
        if section.get("flashcards"):
            transformed["flashcards"] = section["flashcards"]
        
        presentation["sections"].append(transformed)
    
    return presentation


def _transform_narration(narration: dict, visual_beats: list = None) -> dict:
    """Transform narration to player format, mapping visual_beats into segment visual_content."""
    full_text = narration.get("full_text", "")
    segments = narration.get("segments", [])
    visual_beats = visual_beats or []
    
    # Build segment_id -> visual_beat mapping
    beat_map = {}
    for beat in visual_beats:
        seg_id = beat.get("segment_id", "seg_1")
        if seg_id not in beat_map:
            beat_map[seg_id] = beat
    
    transformed_segments = []
    for i, seg in enumerate(segments):
        seg_id = seg.get("segment_id", f"seg_{i+1}")
        beat = beat_map.get(seg_id, {})
        
        # Map visual_beat to visual_content
        visual_type = beat.get("visual_type", "text")
        display_text = beat.get("display_text", "")
        
        # Determine content_type and structure
        if visual_type == "bullet_list":
            content_type = "bullet_points"
            items = [display_text] if display_text else []
            # Split on newlines if present
            if display_text and "\n" in display_text:
                items = [line.strip() for line in display_text.split("\n") if line.strip()]
            visual_content = {
                "content_type": content_type,
                "display_format": "bullets",
                "items": items,
                "verbatim_content": None
            }
        elif visual_type == "equation":
            visual_content = {
                "content_type": "equation",
                "display_format": "latex",
                "items": [],
                "verbatim_content": beat.get("latex_content", display_text)
            }
        elif visual_type in ("diagram", "image"):
            visual_content = {
                "content_type": visual_type,
                "display_format": None,
                "items": [],
                "verbatim_content": display_text,
                "image_id": beat.get("image_id")
            }
        else:
            # Default text type
            visual_content = {
                "content_type": "text",
                "display_format": None,
                "items": [],
                "verbatim_content": display_text if display_text else None
            }
        
        transformed_seg = {
            "segment_id": i + 1,
            "text": seg.get("text", ""),
            "duration_seconds": 0,
            "gesture_hint": seg.get("purpose", "neutral"),
            "visual_content": visual_content,
            "display_directives": seg.get("display_directives", {
                "text_layer": "show",
                "visual_layer": "show" if display_text else "hide",
                "avatar_layer": "show"
            })
        }
        transformed_segments.append(transformed_seg)
    
    return {
        "full_text": full_text,
        "segments": transformed_segments,
        "total_duration_seconds": 0
    }


def _transform_visual_beats(visual_beats: list) -> list:
    """Transform visual beats to player format."""
    transformed = []
    for beat in visual_beats:
        t_beat = {
            "beat_id": beat.get("beat_id", f"beat_{len(transformed)+1}"),
            "segment_id": beat.get("segment_id", 1),
            "visual_beat_type": beat.get("visual_type", "text_only"),
            "description": beat.get("display_text", ""),
            "source_block_ids": []
        }
        
        if beat.get("latex_content"):
            t_beat["latex_content"] = beat["latex_content"]
        if beat.get("image_id"):
            t_beat["image_id"] = beat["image_id"]
        
        transformed.append(t_beat)
    
    return transformed


def _extract_display_directives(section: dict) -> list:
    """Extract display directives from section."""
    narration = section.get("narration", {})
    segments = narration.get("segments", [])
    
    if segments:
        return [seg.get("display_directives", {
            "text_layer": "show",
            "visual_layer": "hide", 
            "avatar_layer": "show"
        }) for seg in segments]
    
    return [{
        "text_layer": "show",
        "visual_layer": "hide",
        "avatar_layer": "show"
    }]
