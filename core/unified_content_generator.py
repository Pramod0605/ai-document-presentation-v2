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

## ⚠️ NON-NEGOTIABLE REQUIREMENTS - READ FIRST ⚠️

**CRITICAL VIDEO PROMPT REQUIREMENT:**
- Every `video_prompt` field MUST contain **MINIMUM 80 WORDS** - no exceptions
- Every `manim_spec` field MUST contain **MINIMUM 80 WORDS** - no exceptions
- Prompts under 80 words will FAIL video generation and waste API credits
- Before finalizing each video_prompt/manim_spec, COUNT THE WORDS - if < 80, add more detail

**SELF-CHECK BEFORE SUBMITTING:**
For each video_prompt you generate, verify:
✓ Does it describe the COMPLETE visual scene in detail?
✓ Does it specify camera movement, lighting, colors, style?
✓ Does it match what the narrator is explaining in that segment?
✓ Is it AT LEAST 80 words? (Count: most 80-word prompts fill 5-6 lines)

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

## RENDERER SELECTION - INTELLIGENT VIDEO EXAMPLES

### TEACHING PATTERN: EXPLAIN → THEN SHOW VIDEO EXAMPLE
For each topic in content sections, follow this pattern:
1. First segment: Explain concept with text/bullets on screen (narration teaches)
2. Second segment: Show video example demonstrating the concept (narration describes what we see)

This makes boring educational content INTERACTIVE and ENGAGING!

### WHEN TO GENERATE VIDEO EXAMPLES (derived_renderer="video")
For BIOLOGY content sections, ALWAYS generate video_prompts for:
- Anatomy (Neurons, Brain, Heart, Cells) → "3D animation of [structure] showing..."
- Processes (Reflex Arc, Digestion, Photosynthesis) → "Animation showing [process] step by step..."
- Organisms/Microscopic (Cells, Hormones, Blood) → "Microscopic view of [subject] revealing..."

For PHYSICS content sections, generate video for:
- Motion/Forces → "Simulation showing [phenomenon] in action..."
- Waves/Energy → "Visualization of [concept] propagating..."

For CHEMISTRY content sections:
- Reactions → "Molecular animation showing [reaction] occurring..."
- Lab processes → "Video of [experiment] demonstrating..."

For MATH content sections, use derived_renderer="manim":
- Equations → manim_spec with step-by-step solving
- Graphs → manim_spec showing function plotting
- Geometry → manim_spec with shape construction

### CONTENT SECTION STRUCTURE WITH VIDEO EXAMPLES
```
Section: "The Nervous System"
├── Segment 1: Explain (text_layer: show) - "The nervous system is..."
│   └── visual_beat: bullet_list with key points
├── Segment 2: Video Example (visual_layer: show, text_layer: hide)
│   └── video_prompt: [80+ word detailed prompt based on narration]
├── Segment 3: Explain next concept (text_layer: show)
│   └── visual_beat: diagram description
└── Segment 4: Video Example (visual_layer: show, text_layer: hide)
    └── video_prompt: [80+ word detailed prompt based on narration]
```

### VIDEO PROMPT REQUIREMENTS (WAN - Biology/Physics/Chemistry)
CRITICAL: Each video_prompt MUST be **80+ words minimum** for the video API to generate quality results.

Each video_prompt must:
1. **Be 80+ words minimum** - detailed enough for AI video generation
2. **Be derived from the narration context** - visualize exactly what the narrator is explaining
3. **Duration hint: 10-15 seconds**
4. **Include visual details**: camera angles, lighting, animation style, motion, colors

**NARRATION-VIDEO SYNC RULE:**
The segment's narration (text) explains the concept in audio. The video_prompt describes what the viewer SEES while hearing that narration. They must match in content but differ in format:
- Narration (audio): "The neuron transmits electrical signals through its axon..."
- Video prompt (visual): "Detailed 3D animation of a single neuron with glowing blue cell body and dendrites, showing a bright electrical impulse pulse traveling along the elongated axon fiber as a wave of light, the signal moves smoothly from left to right, reaching terminal buttons at the synapse junction, microscopic scientific visualization style with dark background and bioluminescent effects, camera slowly follows the signal path, smooth continuous 12-second animation loop"

**80+ WORD VIDEO PROMPT EXAMPLE (Biology):**
"Cinematic 3D animation inside the human nervous system showing a detailed neuron cell with its soma glowing softly blue, multiple branching dendrites receiving signals visualized as tiny sparks, the electrical impulse consolidates and travels down the long axon as a bright wave of energy, passing through the myelin sheath segments which appear as translucent white bands, the signal reaches the axon terminals and triggers the release of neurotransmitter molecules shown as small glowing spheres crossing the synaptic cleft to the next neuron, scientific documentary style with dark purple background, smooth camera movement following the signal, duration 12 seconds"

### MANIM SPEC REQUIREMENTS (Math/Physics Equations)
CRITICAL: Each manim_spec MUST be **80+ words minimum** describing the mathematical animation in detail.

Each manim_spec must:
1. **Be 80+ words minimum** - detailed enough for Manim code generation
2. **Be derived from the narration context** - visualize the math/equation being explained
3. **Describe step-by-step animation**: what appears first, transformations, final result
4. **Include visual details**: colors, positions, timing, text labels

**NARRATION-MANIM SYNC RULE:**
The segment's narration explains the mathematical concept. The manim_spec describes the animated visualization that matches:
- Narration (audio): "Let's solve this quadratic equation step by step..."
- Manim spec (visual): detailed description of equation appearing, transformations, solution steps

**80+ WORD MANIM SPEC EXAMPLE (Math):**
"Create an animated mathematical visualization showing the quadratic formula derivation. Start with the general form ax² + bx + c = 0 appearing in white text center screen. After 2 seconds, transform by subtracting c from both sides, showing the intermediate step ax² + bx = -c with arrows indicating the operation. Next, divide all terms by a, each term transforming individually with color highlights: x² in blue, (b/a)x in green, -c/a in red. Complete the square by adding (b/2a)² to both sides, showing this step-by-step with the square visualization. Finally, take the square root and isolate x, revealing the complete quadratic formula x = (-b ± √(b²-4ac)) / 2a in golden yellow, with a box highlighting the final answer. Total duration 15 seconds with smooth transitions between each step."

RECAP SECTION: ALWAYS use "video" with exactly 5 cinematic video_prompts (each 80+ words)

**80+ WORD RECAP VIDEO PROMPT EXAMPLE:**
"Cinematic, warm-toned video of a young Indian student in her room, focused intently on building a small pyramid of wooden blocks arranged in a triangle pattern on her study table. Each row has one fewer block than the row below, creating a clear arithmetic progression visual. Soft afternoon sunlight filters through a window, casting gentle shadows across the scene. The camera slowly zooms in on her hands carefully placing each block, emphasizing the mathematical pattern. The room has warm colors with educational posters visible in the background, creating an authentic study environment. Duration 12 seconds with smooth camera movement."

DECISION LOGGING: For each section, explain WHY you chose the renderer in decision_reason.

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

## QUIZ HANDLING - PROGRESSIVE REVEAL PATTERN
- Extract Q&A pairs from document's exercise/question sections
- Format as structured quiz with question, options, correct_answer, explanation
- Split into multiple quiz sections if >8 questions

**CRITICAL: Quiz sections MUST generate per-question narration segments for progressive reveal:**

For EACH question in the quiz, generate exactly 3 narration segments:
1. **Question Segment** (purpose: "introduce"): Read the question aloud
   - display_directives: text_layer="show" (show question + options)
   - Example: "Let's look at question 1. The growth of pollen tubes towards ovules is an example of which type of tropism? Take a moment to consider the options."

2. **Pause Segment** (purpose: "emphasize"): Give thinking time
   - duration: ~3-5 seconds of thinking prompt
   - display_directives: text_layer="show" (keep question visible)
   - Example: "Think about what you learned about plant movements and tropisms."

3. **Answer Segment** (purpose: "explain"): Reveal and explain the answer
   - display_directives: text_layer="show", answer_revealed=true
   - Example: "The correct answer is C, chemotropism. This is because pollen tubes grow in response to chemical signals released by the ovule."

**QUIZ SEGMENT EXAMPLE:**
For a quiz with 2 questions, generate 6 segments total (3 per question):
- seg_1: Read question 1 + options
- seg_2: Pause for thinking (question 1)
- seg_3: Reveal answer 1 with explanation
- seg_4: Read question 2 + options
- seg_5: Pause for thinking (question 2)
- seg_6: Reveal answer 2 with explanation

Each segment MUST include a "question_index" field (0-based) to sync with quiz_data.questions

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
      "decision_reason": "Brief explanation of WHY this renderer was chosen for this section (for analysis)",
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
  ],
  "decision_log": {
    "total_video_prompts": 0,
    "total_manim_specs": 0,
    "renderer_choices": [
      {
        "section_id": "section_1",
        "section_title": "Section Title",
        "renderer": "none|manim|video",
        "reason": "Detailed explanation of why this renderer was selected"
      }
    ],
    "content_analysis": "Brief summary of document content and key topics identified"
  }
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
) -> Tuple[str, dict]:
    """Call OpenRouter API and return (response_text, usage_stats)."""
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
    content = data["choices"][0]["message"]["content"]
    
    # ISS-300: Extract usage stats for analytics
    usage = data.get("usage", {})
    usage_stats = {
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "model": config.model
    }
    
    return content, usage_stats


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
    llm_usage_stats = None
    
    for attempt in range(config.max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{config.max_retries}: Calling LLM...")
            
            response, usage_stats = call_openrouter_llm(
                system_prompt=UNIFIED_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                config=config
            )
            llm_usage_stats = usage_stats
            
            logger.info(f"Response received: {len(response)} chars")
            
            output = extract_json_from_response(response)
            logger.info("JSON parsed successfully")
            
            output = normalize_output(output)
            
            is_valid, errors = validate_schema(output)
            
            if not is_valid:
                raise SchemaValidationError(f"Schema validation failed: {errors[:3]}")
            
            logger.info("Schema validation passed")
            
            # ISS-300: Attach usage stats to output for analytics
            output["_llm_usage"] = llm_usage_stats
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
    
    # Preserve decision_log from LLM for analysis
    decision_log = v2_output.get("decision_log", {})
    
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
        "decision_log": decision_log,
        "sections": []
    }
    
    for i, section in enumerate(v2_output.get("sections", [])):
        transformed = {
            "section_id": i + 1,
            "section_type": section.get("section_type", "content"),
            "title": section.get("title", f"Section {i+1}"),
            "renderer": section.get("derived_renderer", "none"),
            "decision_reason": section.get("decision_reason", ""),
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
        
        # TEACH → SHOW pattern: text_layer and visual_layer are mutually exclusive
        # When showing text, visual should be hidden (TEACH phase)
        # When showing video/visual, text should be hidden (SHOW phase)
        seg_directives = seg.get("display_directives")
        if not seg_directives:
            # Default to TEACH mode: show text, hide visual
            seg_directives = {
                "text_layer": "show",
                "visual_layer": "hide",
                "avatar_layer": "show"
            }
        else:
            # Enforce mutual exclusion if LLM violated it
            if seg_directives.get("text_layer") == "show" and seg_directives.get("visual_layer") == "show":
                # Default to TEACH mode when both are show
                seg_directives["visual_layer"] = "hide"
        
        transformed_seg = {
            "segment_id": i + 1,
            "text": seg.get("text", ""),
            "duration_seconds": 0,
            "gesture_hint": seg.get("purpose", "neutral"),
            "visual_content": visual_content,
            "display_directives": seg_directives
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
