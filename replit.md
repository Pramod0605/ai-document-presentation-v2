# AI Animated Education - Phase 1 (v1.4)

## Overview
This project is a **Deterministic Educational Film Engine** designed to transform PDF chapters into pedagogically structured, animated explanation videos with synchronized narration. Its core purpose is to automate the creation of high-quality educational content, targeting a market for accessible and engaging learning materials. Version 1.4 introduces a **Split Director Architecture** to enhance output reliability and precision.

## User Preferences
The user wants an iterative development process. The agent should prioritize clear, concise, and accurate communication. Before making any major architectural changes or introducing new dependencies, the agent must ask for explicit approval. The user prefers detailed explanations for complex technical decisions. The agent should ensure that all code is well-documented and follows best practices for maintainability and readability.

### NON-NEGOTIABLE RULES (CRITICAL)
1. **Before proposing ANY solution**, the agent MUST check:
   - `attached_assets/` folder for specification documents (especially LLM brain prompts)
   - `docs/llm_output_requirements_v1.4.json` for definitive LLM output specification (v1.4)
   - `docs/llm_output_requirements_v1.3.json` for legacy v1.3 specification
   - `replit.md` for documented architecture and decisions
   - Existing prompt files in `core/prompts/` (v1.3 prompts)
   - `issues.json` for tracked problems and their agreed solutions
2. The agent must NOT assume or invent solutions - all proposals must reference documented specifications.
3. Nothing is a "solution" until the user explicitly agrees.
4. When in doubt, ASK the user - do not proceed with assumptions.
5. The LLM is the "brain" - timing, durations, and creative decisions come from LLM output, not from post-processing calculations.
6. **ALL LLM OUTPUTS MUST CONFORM TO `docs/llm_output_requirements_v1.4.json` OR FAIL** - this is non-negotiable. There are NO FALLBACKS. Missing required fields = generation failure.
7. **Player is a DUMB display layer** - it consumes LLM output without modification. No duration calculations, no content fallbacks, no graceful degradation.
8. **Issue Tracking First** - Any issue noticed MUST be logged to `issues.json` with full details BEFORE proposing any solution.
9. **Upstream/Downstream Impact Analysis** - Before code changes, verify upstream and downstream components are not affected. If they are, include those fixes in the proposal and ask for user approval.
10. **No Deviation Without Approval** - No deviations from the initial goal. Any code changes must be approved by the user first.

## System Architecture

### Pipeline Architecture (v1.4 Split Director)

| Pass | Phase | Model | Role | Output |
|------|-------|-------|------|--------|
| **0** | Smart Chunker | Gemini 2.5 Pro | Extract logical topics with metadata | topics.json |
| **1a** | Content Director | Gemini 2.5 Pro | Generate intro/summary/content/example/quiz | content_sections.json |
| **1b** | Recap Director | Gemini 2.5 Pro | Generate memory (5 flashcards) + recap (5 scenes) | recap_sections.json |
| **Merge** | Merge Step | Python | Deterministic merge of 1a + 1b | presentation.json |
| **1.5** | TTS Duration | Narakeet + Mutagen | Generate audio, measure actual duration | Updated presentation.json |
| **2** | Renderers | Various | Deterministic rendering | MP4 videos |
| **3** | Player | N/A | DUMB execution - follows JSON instructions | Video playback |

### Core Architectural Principles
- **PLAYER IS DUMB**: The player only executes JSON instructions; it does not determine layout, timing, or pedagogy.
- **ONE PRIMARY ATTENTION LAYER AT A TIME**: Either text OR visuals are prominent, never simultaneously.
- **TEACH → THEN SHOW**: Narration explains first, then visuals reinforce.
- **EVERYTHING IS TIMED**: All segments have precise durations, with visuals synchronized.
- **TWO-CHANNEL SEPARATION**: Narration is audio-only; `visual_content` is screen display only.

### Key Features and Design Decisions
- **Split Director Architecture**: Divides the Director LLM into `Content Director` (intro, summary, content, example, quiz) and `Recap Director` (memory, recap scenes) to reduce cognitive load and improve LLM compliance.
- **TTS Duration Measurement**: Actual TTS audio is generated via Narakeet, and mutagen is used to measure precise durations, updating the presentation JSON.
- **Targeted Retry Strategy**: Implements specific retry counts for `Smart Chunker`, `Content Director`, and `Recap Director` for structural and semantic errors.
- **JSON Repair Pre-Validation**: Includes steps to strip markdown fences, fix trailing commas, and close unclosed brackets before validation.
- **Display Directives**: Each narration segment includes explicit `display_directives` for `text_layer`, `visual_layer`, and `avatar_layer` control. A critical rule is that text MUST hide before complex visuals appear.
- **Mandatory Sections**: `intro`, `summary`, `memory` (5 flashcards), and `recap` (5 scenes) are strictly required.
- **Avatar Rules**: Specific avatar visibility and size rules apply to different section types (e.g., `INTRO`: visible, center, ≥50% width; `RECAP`: hidden).
- **Manim Hard Rule**: Manim renderer requires `manim_scene_spec` for every visual beat.
- **Two-Channel Content Separation**: `narration.segments[].text` is for TTS only, while `visual_content` is for on-screen display.
- **Renderer Hardening**: Strict validation rules for Remotion (JSON-only output) and WAN/Video (minimum word count, no vague phrases).
- **Schema Validation**: Uses `schemas/presentation_v1.3.schema.json` for strict JSON Schema validation, with limited retries for structural repair.
- **Renderer Decision Rules**: The Director LLM dynamically selects the renderer: Manim for math/physics, Video (WAN) for biology/chemistry/recap, and Remotion for intro/summary/memory/quiz motion graphics.
- **Khan Academy-Style Theme**: A dark theme is used for the player with specific color codes and font choices (Lato, Caveat).
- **Technical Stack**: Python Flask API backend, vanilla HTML5/JavaScript frontend, OpenRouter for LLM pipeline, Narakeet for TTS, MoviePy for video editing.
- **Fail-Fast Policy**: Strict fail-fast behavior with no fallbacks for critical components.

## External Dependencies
- **OpenRouter**: For LLM access (Gemini 2.5 Flash, Gemini 2.5 Pro, Claude Sonnet).
- **Narakeet API**: Text-to-Speech service.
- **Kie.ai API (WAN)**: Conceptual video generation.
- **Datalab API**: PDF to Markdown conversion.
- **Flask**: Web framework for the backend.
- **Flask-CORS**: Handles Cross-Origin Resource Sharing.
- **MoviePy**: Video editing library.
- **OpenAI Python Client**: Used for OpenRouter gateway.
- **Tenacity**: For API call retry logic.
- **Mutagen**: For TTS audio duration measurement.

## V1.4 API Endpoints
- `GET /api/v14/pipeline-info` - Returns pipeline architecture information
- `POST /api/v14/generate` - Run full V1.4 Split Director pipeline
  - Parameters: `markdown` (required), `subject`, `grade`, `skip_wan`, `tts_provider`
  - `tts_provider`: "narakeet" (production quality), "pyttsx3" (local/offline for testing), "estimate" (word-count only, skips audio)
- `POST /api/v14/dry-run-test` - Test pipeline structure without LLM calls

## TTS Provider Options
- **narakeet**: Production-quality Indian English voice (Ravi). Requires NARAKEET_API_KEY. Falls back to pyttsx3 on failure.
- **pyttsx3**: Local/offline TTS for testing. Duration measurement only, quality irrelevant. Saves to .wav files.
- **estimate**: Word-count based duration estimation (~130 wpm). No audio generation. Fastest for dry runs.

## Test Scripts
- `scripts/test_v14_pipeline.py` - End-to-end pipeline test script
  - `--mode info_only` - Check pipeline info only
  - `--mode dry_run` - Test endpoints without LLM calls
  - `--mode full_test` - Run actual pipeline with LLMs (incurs costs)
  - `--markdown-file <path>` - Use custom markdown file instead of sample
  - `--tts-provider <narakeet|pyttsx3|estimate>` - Select TTS provider
  - `--skip-wan` - Skip WAN video rendering
  - `--report <path>` - Save test report to file

## Recent Changes (2025-12-22)
- Created `docs/llm_output_requirements_v1.4.json` documenting Split Director architecture
- Added V1.4 API endpoints to `api/app.py`
- Created dry run test script for pipeline validation
- Exposed `validate_presentation_v14` as public function
- Added TTS provider selection (narakeet/pyttsx3/estimate) with proper fallback chain
- Implemented pyttsx3 for local/offline duration measurement during testing
- Enhanced test script with --markdown-file, --tts-provider, --skip-wan, --report parameters