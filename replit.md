# AI Animated Education - Phase 1

## Project Overview

A production-grade AI pipeline that converts PDF chapters into pedagogically structured explanation videos with synchronized narration. The system uses LLM as the "Director" to make all creative decisions about content presentation.

## Architecture

- **Backend**: Python Flask API
- **Frontend**: Vanilla HTML5/JavaScript video player
- **LLM**: Two-model pipeline via OpenRouter:
  - **Gemini 2.5 Flash** (chunker): Fast, cheap model for intelligent topic boundary detection
  - **Gemini 2.5 Pro** (director): Powerful model for detailed visual/narration generation
- **Video**: Dual renderer system (Manim for math, WAN/kie.ai for science concepts)
- **Audio**: Narakeet TTS with Indian male voice (ravi), gTTS fallback

## Two-LLM Pipeline

Large documents (>30K chars) are processed in chunks to avoid output truncation:
1. **Flash Chunker** - Analyzes markdown, identifies logical topic boundaries
2. **Pro Director** - Generates full presentation JSON for each chunk
3. **Merger** - Combines all chunk outputs into unified presentation

Files:
- `core/prompts/chunker_prompt.txt` - Instructions for topic boundary detection
- `core/llm_client.py:generate_chunked_presentation()` - Orchestrator function
- `core/llm_client.py:chunk_markdown_with_flash()` - Flash chunking call
- `core/llm_client.py:slice_markdown_by_chunks()` - Content slicing logic

## Pedagogical Structure

The system generates content in a mandatory 5-section flow:
1. **Intro** - Warm, motivating introduction (60-100 words)
2. **Summary** - Learning objectives and real-life connections
3. **Content** - Multiple teaching topics (150-250+ words each, with examples)
4. **Memory** - 3 flashcards/mnemonics for recall
5. **Recap** - Story-based recap with 5 visual scenes

## Key Components

### API Layer (`api/app.py`)
- POST `/process_pdf` - Upload and process PDF files
- POST `/process_markdown` - Process markdown content
- GET `/health` - Health check
- GET `/player/*` - Serve video player

### Core Pipeline (`core/`)
- `llm_client.py` - OpenRouter LLM integration for content direction
  - Validates section_type (intro, summary, content, memory, recap)
  - Tracks narration word counts in generation_trace.json
- `pipeline.py` - Main orchestrator for the PDF-to-video flow
- `datalab_client.py` - PDF to Markdown conversion
- `renderer_executor.py` - Dispatch to appropriate renderer
- `prompts/` - System and user prompts for LLM

### Renderers (`render/`)
- `manim/manim_runner.py` - Mathematical animations
- `wan/wan_client.py` - kie.ai API for conceptual videos

### TTS (`tts/generate_audio.py`)
- Primary: Narakeet API with Indian male voice (ravi)
- Fallback: gTTS with Indian English (tld='co.in')
- Generates section_[id].mp3 files

### Player (`player/`)
- YouTube-style HTML5 video player
- Handles section_type variations:
  - intro: mode-center layout
  - summary: mode-side layout
  - content: mode-side with segments
  - memory: mode-center with flashcards
  - recap: mode-image with scene transitions
- Subtitle sync, layout zones, dev mode
- Chroma key avatar overlay

## JSON Schema

### Presentation (sections array)
```json
{
  "chapter_title": "string",
  "subject": "string",
  "grade": "string",
  "language": "en-IN",
  "sections": [
    {
      "section_type": "intro|summary|content|memory|recap",
      "id": 1,
      "title": "Section Title",
      "renderer": "wan_video|manim",
      "explanation_plan": {},
      "layout": {},
      "narration": "...",
      "segments": [],
      "flashcards": [],
      "recap_scenes": []
    }
  ]
}
```

## Running the Project

The Flask server runs on port 5000. Access the player at `/player/index.html`.

## Environment Variables

- `OPENROUTER_API_KEY` - For LLM content generation
- `NARAKEET_API_KEY` - For Indian male voice TTS (required for male voice)
- `KIE_API_KEY` - For WAN video generation (optional, uses placeholder if not set)
- `DATALAB_API_KEY` - For PDF conversion (optional, uses stub if not set)

## Dependencies

- flask, flask-cors
- gtts, moviepy
- openai, tenacity, requests
- python-dotenv

## Recent Changes

- 2025-12-16: **Per-Beat Video Rendering (WAN/Manim)**:
  - WAN runner now generates one video per visual beat (not per section)
  - Each beat compiled via visual_compiler into structured prompt
  - Output files: `topic_{id}_beat_{idx}.mp4` for each beat
  - Manim runner handles multi_beat plans from visual_compiler
  - Fail-fast: Manim rejects placeholder equations (E=mc², etc.)
  - Fail-fast: WAN rejects sections without visual beats
  - Logging: Each beat logged separately as `wan_beat` renderer
  - MIN_FIELD_WORDS relaxed from 8 to 4 (combined prompts are 40-80+ words)
- 2025-12-16: **Two-LLM Chunked Pipeline (Solves Truncation)**:
  - Flash chunker identifies logical topic boundaries (2000-4000 words each)
  - Pro director generates presentation for each chunk with chunk-aware prompts
  - Dynamic prompt modification: replaces SECTION GENERATION RULES per chunk type
  - First chunk: intro + summary + content
  - Middle chunks: content only
  - Last chunk: content + memory + recap
  - Post-merge validation with smart deduplication
  - Sequential section ID renumbering across all chunks
  - Threshold: Documents >30K chars trigger chunked pipeline
  - Fixed auto-repair: now validates 5-field visual beat format (scene_setup, objects_and_properties, motion_sequence, labels_and_text, pedagogical_focus)
  - Placeholder beats use proper 5-field format for compilation compatibility
- 2025-12-15: **Structural Coercion for Visual Beats (Gemini-safe)**:
  - Replaced word-count validation with 5 mandatory sub-fields
  - New schema: scene_setup, objects_and_properties, motion_sequence, labels_and_text, pedagogical_focus
  - Each field must be at least 8 words (Gemini naturally produces 80-120 words total)
  - Validation checks for missing/empty fields instead of word counts
  - Updated prompts with good/bad examples in the new format
  - Unit tests updated and all 6 passing
- 2025-12-15: **Fixed LLM Truncation Issue (Root Cause)**:
  - CONFIRMED: Server logs showed "[JSON FIX]: Detected truncated JSON - 163 { vs 161 }"
  - Increased max_tokens from 16384 to 32768 (doubled output limit)
  - Added fail-fast: raises ValidationError when truncation detected instead of silently continuing
  - Added truncation tracking in generation_trace with details (missing braces/brackets count)
  - Clear log message: "[TRUNCATION WARNING]: Response was TRUNCATED!"
- 2025-12-15: **Fixed File Persistence on Validation Failure**:
  - ValidationError now carries presentation and trace data
  - pipeline.py saves presentation.json and generation_trace.json BEFORE re-raising validation errors
  - Failed jobs now have debug files available for investigation
  - Job History section added to dashboard showing past jobs with error previews
  - Jobs persist to jobs_index.json (survive server restarts)
- 2025-12-15: **Governance Upgrade - Fail-Fast for Vague Visual Beats**:
  - core/visual_compiler.py - Converts visual_beats to concrete WAN/Manim prompts
  - VISUAL_INSTRUCTION_MIN_WORDS = 50 for content/example sections
  - Expanded BANNED_VAGUE_PHRASES (19 phrases including "show clearly", "animate smoothly", etc.)
  - VisualCompilationError for vague beats - NO best-effort fallbacks
  - renderer_executor.py integrates visual compiler with strict_mode parameter
  - V2 prompts include concrete good/bad examples and quality gate checklist
  - tests/test_visual_compiler.py - Unit tests confirming strict validation works (6 tests, all passing)
- 2025-12-15: Added job dashboard at /dashboard with:
  - File upload (PDF/Markdown)
  - Subject/Grade inputs
  - Options: Dry Run, Skip WAN, Skip Avatar
  - Job status display with progress bar
  - Play button to open completed jobs in new window
  - Job output files stored in player/jobs/<job_id>/
- 2025-12-15: Added render prompt logging to `player/assets/render_prompts.json`
  - WAN prompts logged before video generation
  - Manim plans and generated code logged for debugging
  - Trace cleared at start of each job
- 2025-12-15: V2 LLM prompts with strict visualization rules and validation
- 2025-12-15: Added example section type with step-by-step visualization
- 2025-12-15: Field-level validation for narration_segments and visual_beats
- 2025-12-15: Example sections get distinct green styling in player
- 2025-12-15: Added job-based async processing with real-time progress UI
- 2025-12-15: UI now supports both PDF and Markdown file uploads (.pdf, .md, .markdown, .txt)
- 2025-12-15: Added /submit_job and /job/<id>/status API endpoints
- 2025-12-15: Fixed video playback sync issues for content videos
- 2025-12-14: Switched TTS to Narakeet with Indian male voice (ravi)
- 2025-12-14: Fixed Kie Runway API (duration must be 5, 8, or 10 seconds)
- 2025-12-14: Upgraded to pedagogical structure (Intro/Summary/Content/Memory/Recap)
- 2025-12-14: Added section_type validation and narration word count tracking
- 2025-12-14: Player now handles all section types with appropriate layouts

## Job-Based Processing

The system now uses async job processing:
- POST `/submit_job` - Submit PDF or Markdown file, returns job_id immediately
- GET `/job/<id>/status` - Poll for progress (progress %, current step, completion)
- Only one job runs at a time (serialized execution)
- Progress bar shows real-time step updates in UI
