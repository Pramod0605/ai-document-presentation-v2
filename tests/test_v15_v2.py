"""
V1.5 Optimized V2 - POC Test File

Tests the new unified content generation approach:
- Stage 1: Content Cleaner (optional)
- Stage 2: Unified Content Generator (MAIN - single LLM call)
- Stage 3: Validation
- Stage 4: Schema Comparison

Run: python tests/test_v15_v2.py
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


UNIFIED_SYSTEM_PROMPT = """You are an expert Educational Video Script Generator for Indian students (Grade 8-12).

Your task: Convert a textbook chapter into a COMPLETE presentation JSON in a SINGLE response.

## SECTION TYPES (Generate in this order)
1. **intro** - Welcome message, topic introduction (1 section)
2. **summary** - Learning objectives as bullet points (1 section)
3. **content** - Main teaching content (2-5 sections based on document length)
4. **example** - Worked examples if present in document (0-2 sections)
5. **quiz** - Questions extracted from document Q&A pairs (1-3 sections, ~4 Q&A per section)
6. **memory** - Flashcard-style key concept review (1 section, 3-5 cards)
7. **recap** - Video summary with storytelling (1 section)

## RENDERER SELECTION
- "none" - For text, bullets, simple content (most sections)
- "manim" - For mathematical equations, graphs, geometric animations
- "video" - For recap section only (generates AI video)

## SEGMENT RULES
- Each segment = 15-30 seconds when spoken aloud
- Narration EXPLAINS, visuals REINFORCE (never duplicate)
- Avatar is ALWAYS visible: avatar_layer = "show"

## VISUAL BEAT TYPES
- "text" - Single line or paragraph
- "bullet_list" - Multiple points
- "equation" - LaTeX math (use latex_content field)
- "diagram" - Description for visual generation
- "image" - Reference to document image (use image_id field)
- "video" - AI-generated video (recap only)

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
          "image_id": null,
          "layer_visibility": {
            "text_layer": "show",
            "visual_layer": "hide",
            "avatar_layer": "show"
          }
        }
      ],
      "segment_enrichments": [
        {
          "segment_id": "seg_1",
          "key_terms": ["term1", "term2"],
          "visual_cues": ["highlight", "zoom"],
          "transition_type": "fade|slide|none"
        }
      ],
      "quiz_data": null,
      "flashcards": null,
      "video_prompts": null
    }
  ]
}

For quiz sections, include quiz_data:
"quiz_data": {
  "questions": [
    {
      "question": "Question text?",
      "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
      "correct_answer": "B",
      "explanation": "Why B is correct..."
    }
  ]
}

For memory sections, include flashcards:
"flashcards": [
  {"front": "Term/Concept", "back": "Definition/Explanation"}
]

For recap sections, include video_prompts:
"video_prompts": [
  {
    "prompt": "Detailed 100+ word prompt describing the educational video scene...",
    "duration_hint": 15,
    "style": "educational"
  }
]
"""


UNIFIED_USER_PROMPT_TEMPLATE = """Create a complete educational presentation for:

## SUBJECT: {subject}
## GRADE: {grade}

## IMAGES AVAILABLE IN DOCUMENT:
{images_list}

## DOCUMENT CONTENT:
{markdown_content}

---

Generate the complete presentation JSON with all sections (intro, summary, content, example, quiz, memory, recap).
Ensure every segment has avatar_layer: "show".
Output ONLY valid JSON, no explanations."""


UNIFIED_SYSTEM_PROMPT_CONCISE = """You are an Educational Video Script Generator. Convert textbook content to a presentation JSON.

OUTPUT ONLY VALID JSON. No explanations.

SECTION TYPES (in order): intro, summary, content (2-4), quiz, memory, recap

MINIMAL STRUCTURE PER SECTION:
{
  "section_id": "section_N",
  "section_type": "intro|summary|content|quiz|memory|recap",
  "title": "Title",
  "derived_renderer": "none|manim|video",
  "narration": {
    "full_text": "Full narration...",
    "segments": [{"segment_id": "seg_1", "text": "...", "purpose": "explain", "display_directives": {"text_layer": "show", "visual_layer": "hide", "avatar_layer": "show"}}]
  },
  "visual_beats": [{"beat_id": "beat_1", "segment_id": "seg_1", "visual_type": "text", "display_text": "...", "layer_visibility": {"text_layer": "show", "visual_layer": "hide", "avatar_layer": "show"}}],
  "segment_enrichments": [{"segment_id": "seg_1", "key_terms": [], "visual_cues": [], "transition_type": "fade"}],
  "quiz_data": null,
  "flashcards": null,
  "video_prompts": null
}

For quiz: add quiz_data with questions array
For memory: add flashcards array
For recap: add video_prompts array with detailed prompts

RULES:
- avatar_layer ALWAYS "show"
- 2-4 segments per section
- Keep narration natural and educational
- Extract quiz questions from document Q&A
"""


SAMPLE_MARKDOWN = """# Control and Coordination

## Introduction
The nervous system and endocrine system work together to control and coordinate body functions. The nervous system uses electrical signals while the endocrine system uses chemical messengers called hormones.

## The Nervous System

### Structure of a Neuron
A neuron is the basic unit of the nervous system. It consists of:
- **Cell body (Soma)**: Contains the nucleus
- **Dendrites**: Receive signals from other neurons
- **Axon**: Transmits signals away from the cell body
- **Synapse**: Junction between two neurons

### Types of Neurons
1. **Sensory neurons**: Carry signals from sense organs to the brain
2. **Motor neurons**: Carry signals from brain to muscles
3. **Interneurons**: Connect sensory and motor neurons

### Reflex Action
A reflex action is an automatic, rapid response to a stimulus. Example: When you touch a hot object, you immediately pull your hand away.

The reflex arc includes:
1. Receptor (skin)
2. Sensory neuron
3. Spinal cord (relay neuron)
4. Motor neuron
5. Effector (muscle)

## The Endocrine System

### Hormones
Hormones are chemical messengers produced by endocrine glands. They travel through blood to target organs.

### Major Endocrine Glands
| Gland | Hormone | Function |
|-------|---------|----------|
| Pituitary | Growth hormone | Controls growth |
| Thyroid | Thyroxine | Regulates metabolism |
| Pancreas | Insulin | Controls blood sugar |
| Adrenal | Adrenaline | Fight or flight response |

## Questions

Q.1 What is the function of dendrites?
Ans: Dendrites receive signals from other neurons and transmit them to the cell body.

Q.2 Name the hormone that controls blood sugar level.
Ans: Insulin, produced by the pancreas.

Q.3 What is a reflex action? Give an example.
Ans: A reflex action is an automatic, rapid response to a stimulus. Example: Pulling hand away from a hot object.

Q.4 Differentiate between nervous and endocrine system.
Ans: The nervous system uses electrical signals for fast responses, while the endocrine system uses hormones for slower, longer-lasting effects.
"""


def call_openrouter_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = "google/gemini-2.5-pro-preview",
    temperature: float = 0.7,
    max_tokens: int = 32000
) -> str:
    """Call OpenRouter API and return raw response text."""
    import requests
    
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://replit.com",
        "X-Title": "AI Education V1.5 V2 Test"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    logger.info(f"Calling OpenRouter with model: {model}")
    logger.info(f"System prompt length: {len(system_prompt)} chars")
    logger.info(f"User prompt length: {len(user_prompt)} chars")
    
    response = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=300
    )
    
    if response.status_code != 200:
        raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")
    
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    
    finish_reason = result["choices"][0].get("finish_reason", "unknown")
    usage = result.get("usage", {})
    logger.info(f"Finish reason: {finish_reason}")
    logger.info(f"Tokens used - Input: {usage.get('prompt_tokens', 'N/A')}, Output: {usage.get('completion_tokens', 'N/A')}")
    
    if finish_reason == "length":
        logger.warning("WARNING: Response was truncated due to max_tokens limit!")
    
    return content


def extract_json_from_response(response: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    content = response.strip()
    
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    
    if content.endswith("```"):
        content = content[:-3]
    
    content = content.strip()
    
    return json.loads(content)


def normalize_output(output: dict) -> dict:
    """Normalize LLM output to expected schema (handle field name variations)."""
    if "title" in output and "presentation_title" not in output:
        output["presentation_title"] = output.pop("title")
    
    if "presentation" in output and "sections" not in output:
        output["sections"] = output.pop("presentation")
    
    return output


def validate_presentation_schema(output: dict) -> Tuple[bool, List[str]]:
    """Validate presentation JSON against required schema."""
    errors = []
    warnings = []
    
    output = normalize_output(output)
    
    if "presentation_title" not in output:
        errors.append("Missing 'presentation_title'")
    
    if "sections" not in output:
        errors.append("Missing 'sections' array")
        return False, errors
    
    sections = output.get("sections", [])
    if len(sections) < 5:
        warnings.append(f"Only {len(sections)} sections (expected at least 5)")
    
    section_types_found = set()
    
    for i, section in enumerate(sections):
        section_id = section.get("section_id", f"section_{i+1}")
        
        required_fields = ["section_id", "section_type", "derived_renderer", "narration", "visual_beats"]
        for field in required_fields:
            if field not in section:
                errors.append(f"[{section_id}] Missing required field: {field}")
        
        section_type = section.get("section_type")
        if section_type:
            section_types_found.add(section_type)
            
            valid_types = ["intro", "summary", "content", "example", "quiz", "memory", "recap"]
            if section_type not in valid_types:
                errors.append(f"[{section_id}] Invalid section_type: {section_type}")
        
        renderer = section.get("derived_renderer")
        if renderer and renderer not in ["none", "manim", "video"]:
            errors.append(f"[{section_id}] Invalid derived_renderer: {renderer}")
        
        narration = section.get("narration", {})
        if "full_text" not in narration:
            errors.append(f"[{section_id}] Missing narration.full_text")
        if "segments" not in narration:
            errors.append(f"[{section_id}] Missing narration.segments")
        else:
            for j, seg in enumerate(narration.get("segments", [])):
                if "segment_id" not in seg:
                    errors.append(f"[{section_id}] Segment {j} missing segment_id")
                if "text" not in seg:
                    errors.append(f"[{section_id}] Segment {j} missing text")
                
                dd = seg.get("display_directives", {})
                if dd.get("avatar_layer") != "show":
                    warnings.append(f"[{section_id}] Segment {j} avatar_layer is not 'show'")
        
        visual_beats = section.get("visual_beats", [])
        for k, beat in enumerate(visual_beats):
            if "beat_id" not in beat:
                errors.append(f"[{section_id}] Beat {k} missing beat_id")
            if "segment_id" not in beat:
                errors.append(f"[{section_id}] Beat {k} missing segment_id")
            if "visual_type" not in beat:
                errors.append(f"[{section_id}] Beat {k} missing visual_type")
        
        if section_type == "quiz":
            if not section.get("quiz_data"):
                warnings.append(f"[{section_id}] Quiz section missing quiz_data")
        
        if section_type == "memory":
            if not section.get("flashcards"):
                warnings.append(f"[{section_id}] Memory section missing flashcards")
        
        if section_type == "recap":
            if not section.get("video_prompts"):
                warnings.append(f"[{section_id}] Recap section missing video_prompts")
    
    required_types = {"intro", "summary", "content", "memory", "recap"}
    missing_types = required_types - section_types_found
    if missing_types:
        warnings.append(f"Missing section types: {missing_types}")
    
    if warnings:
        for w in warnings:
            logger.warning(f"VALIDATION WARNING: {w}")
    
    return len(errors) == 0, errors


def analyze_output_stats(output: dict) -> dict:
    """Analyze the generated presentation statistics."""
    output = normalize_output(output)
    sections = output.get("sections", [])
    
    stats = {
        "total_sections": len(sections),
        "section_types": {},
        "total_segments": 0,
        "total_visual_beats": 0,
        "total_word_count": 0,
        "renderers": {"none": 0, "manim": 0, "video": 0},
        "quiz_questions": 0,
        "flashcards": 0
    }
    
    for section in sections:
        section_type = section.get("section_type", "unknown")
        stats["section_types"][section_type] = stats["section_types"].get(section_type, 0) + 1
        
        narration = section.get("narration", {})
        segments = narration.get("segments", [])
        stats["total_segments"] += len(segments)
        
        full_text = narration.get("full_text", "")
        stats["total_word_count"] += len(full_text.split())
        
        visual_beats = section.get("visual_beats", [])
        stats["total_visual_beats"] += len(visual_beats)
        
        renderer = section.get("derived_renderer", "none")
        if renderer in stats["renderers"]:
            stats["renderers"][renderer] += 1
        
        quiz_data = section.get("quiz_data", {})
        if quiz_data:
            stats["quiz_questions"] += len(quiz_data.get("questions", []))
        
        flashcards = section.get("flashcards", [])
        if flashcards:
            stats["flashcards"] += len(flashcards)
    
    return stats


def run_unified_content_generator(
    markdown_content: str,
    subject: str = "Science",
    grade: str = "Grade 10",
    images_list: str = "None",
    use_concise_prompt: bool = False
) -> dict:
    """Run the unified content generator - SINGLE LLM CALL."""
    
    user_prompt = UNIFIED_USER_PROMPT_TEMPLATE.format(
        subject=subject,
        grade=grade,
        images_list=images_list,
        markdown_content=markdown_content
    )
    
    system_prompt = UNIFIED_SYSTEM_PROMPT_CONCISE if use_concise_prompt else UNIFIED_SYSTEM_PROMPT
    prompt_type = "CONCISE" if use_concise_prompt else "FULL"
    
    logger.info("=" * 60)
    logger.info(f"STAGE 2: Unified Content Generator ({prompt_type} prompt)")
    logger.info("=" * 60)
    
    response = call_openrouter_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model="google/gemini-2.5-pro-preview",
        temperature=0.7,
        max_tokens=32000
    )
    
    logger.info(f"Response length: {len(response)} chars")
    
    output_file = Path("tests/output") / f"raw_response_{datetime.now().strftime('%H%M%S')}.txt"
    with open(output_file, "w") as f:
        f.write(response)
    logger.info(f"Raw response saved to: {output_file}")
    
    output = extract_json_from_response(response)
    
    return output


def test_with_sample_data(use_concise: bool = True):
    """Test the unified generator with sample markdown."""
    logger.info("=" * 80)
    logger.info("V1.5 OPTIMIZED V2 - POC TEST")
    logger.info("=" * 80)
    
    logger.info("\n--- STAGE 1: Input (Sample Markdown) ---")
    logger.info(f"Markdown length: {len(SAMPLE_MARKDOWN)} chars")
    logger.info(f"Word count: {len(SAMPLE_MARKDOWN.split())} words")
    
    logger.info("\n--- STAGE 2: Unified Content Generator ---")
    try:
        output = run_unified_content_generator(
            markdown_content=SAMPLE_MARKDOWN,
            subject="Biology",
            grade="Grade 10",
            images_list="None",
            use_concise_prompt=use_concise
        )
        logger.info("LLM call successful!")
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    logger.info("\n--- STAGE 3: Validation ---")
    is_valid, errors = validate_presentation_schema(output)
    
    if is_valid:
        logger.info("VALIDATION PASSED")
    else:
        logger.error(f"VALIDATION FAILED: {len(errors)} errors")
        for err in errors:
            logger.error(f"  - {err}")
    
    logger.info("\n--- STAGE 4: Output Analysis ---")
    stats = analyze_output_stats(output)
    
    logger.info(f"Total Sections: {stats['total_sections']}")
    logger.info(f"Section Types: {stats['section_types']}")
    logger.info(f"Total Segments: {stats['total_segments']}")
    logger.info(f"Total Visual Beats: {stats['total_visual_beats']}")
    logger.info(f"Total Word Count: {stats['total_word_count']}")
    logger.info(f"Renderers: {stats['renderers']}")
    logger.info(f"Quiz Questions: {stats['quiz_questions']}")
    logger.info(f"Flashcards: {stats['flashcards']}")
    
    output_dir = Path("tests/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"v15_v2_test_{timestamp}.json"
    
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"\nOutput saved to: {output_file}")
    
    logger.info("\n" + "=" * 80)
    logger.info("POC TEST COMPLETE")
    logger.info("=" * 80)
    
    logger.info(f"""
SUMMARY:
- LLM Calls: 1 (vs 18-22 in current pipeline)
- Sections Generated: {stats['total_sections']}
- Validation: {'PASSED' if is_valid else 'FAILED'}
- Output File: {output_file}
    """)
    
    return output


def test_with_real_pdf(markdown_path: str):
    """Test with real PDF markdown (from previous job)."""
    if not Path(markdown_path).exists():
        logger.error(f"Markdown file not found: {markdown_path}")
        return None
    
    with open(markdown_path, "r") as f:
        markdown_content = f.read()
    
    logger.info(f"Loaded markdown from: {markdown_path}")
    logger.info(f"Content length: {len(markdown_content)} chars")
    
    output = run_unified_content_generator(
        markdown_content=markdown_content,
        subject="Science",
        grade="Grade 10"
    )
    
    is_valid, errors = validate_presentation_schema(output)
    stats = analyze_output_stats(output)
    
    logger.info(f"Validation: {'PASSED' if is_valid else 'FAILED'}")
    logger.info(f"Stats: {stats}")
    
    return output


def compare_with_current_pipeline(v2_output: dict, current_output_path: str):
    """Compare V2 output with current pipeline output."""
    if not Path(current_output_path).exists():
        logger.warning(f"Current output not found for comparison: {current_output_path}")
        return
    
    with open(current_output_path, "r") as f:
        current_output = json.load(f)
    
    current_stats = analyze_output_stats(current_output)
    v2_stats = analyze_output_stats(v2_output)
    
    logger.info("\n--- COMPARISON: Current vs V2 ---")
    logger.info(f"{'Metric':<25} {'Current':>15} {'V2':>15}")
    logger.info("-" * 55)
    logger.info(f"{'Total Sections':<25} {current_stats['total_sections']:>15} {v2_stats['total_sections']:>15}")
    logger.info(f"{'Total Segments':<25} {current_stats['total_segments']:>15} {v2_stats['total_segments']:>15}")
    logger.info(f"{'Total Word Count':<25} {current_stats['total_word_count']:>15} {v2_stats['total_word_count']:>15}")
    logger.info(f"{'Quiz Questions':<25} {current_stats['quiz_questions']:>15} {v2_stats['quiz_questions']:>15}")
    logger.info(f"{'LLM Calls':<25} {'18-22':>15} {'1':>15}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="V1.5 Optimized V2 POC Test")
    parser.add_argument("--sample", action="store_true", help="Run with sample data")
    parser.add_argument("--concise", action="store_true", help="Use concise prompt (smaller output)")
    parser.add_argument("--full", action="store_true", help="Use full detailed prompt")
    parser.add_argument("--markdown", type=str, help="Path to markdown file from real PDF")
    parser.add_argument("--compare", type=str, help="Path to current pipeline output for comparison")
    
    args = parser.parse_args()
    
    use_concise = not args.full
    
    if args.markdown:
        output = test_with_real_pdf(args.markdown)
        if output and args.compare:
            compare_with_current_pipeline(output, args.compare)
    else:
        output = test_with_sample_data(use_concise=use_concise)
