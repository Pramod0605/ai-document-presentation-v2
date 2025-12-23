# AI Animated Education - Phase 1 (v1.4)

## Overview
This project is a **Deterministic Educational Film Engine** that converts PDF chapters into pedagogically structured, animated explanation videos with synchronized narration. Its primary goal is to automate the creation of high-quality, engaging educational content. Version 1.4 introduces a **Split Director Architecture** to enhance the reliability and precision of the output. The project aims to provide accessible learning materials to a broad market.

## User Preferences
The user wants an iterative development process. The agent should prioritize clear, concise, and accurate communication. Before making any major architectural changes or introducing new dependencies, the agent must ask for explicit approval. The user prefers detailed explanations for complex technical decisions. The agent should ensure that all code is well-documented and follows best practices for maintainability and readability.

### Critical Rules
1. Before proposing ANY solution, the agent MUST check:
   - `attached_assets/` for specification documents (especially LLM brain prompts)
   - `docs/llm_output_requirements_v1.4.json` for definitive LLM output specification (v1.4)
   - `docs/llm_output_requirements_v1.3.json` for legacy v1.3 specification
   - `replit.md` for documented architecture and decisions
   - Existing prompt files in `core/prompts/` (v1.3 prompts)
   - `issues.json` for tracked problems and their agreed solutions
2. The agent must NOT assume or invent solutions - all proposals must reference documented specifications.
3. Nothing is a "solution" until the user explicitly agrees.
4. When in doubt, ASK the user - do not proceed with assumptions.
5. The LLM is the "brain" - timing, durations, and creative decisions come from LLM output, not from post-processing calculations.
6. ALL LLM OUTPUTS MUST CONFORM TO `docs/llm_output_requirements_v1.4.json` OR FAIL - this is non-negotiable. There are NO FALLBACKS. Missing required fields = generation failure.
7. Player is a DUMB display layer - it consumes LLM output without modification. No duration calculations, no content fallbacks, no graceful degradation.
8. Issue Tracking First - Any issue noticed MUST be logged to `issues.json` with full details BEFORE proposing any solution.
9. Upstream/Downstream Impact Analysis - Before code changes, verify upstream and downstream components are not affected. If they are, include those fixes in the proposal and ask for user approval.
10. No Deviation Without Approval - No deviations from the initial goal. Any code changes must be approved by the user first.

## System Architecture

### Pipeline Architecture (v1.4 Split Director)

| Pass | Phase | Model | Role | Output |
|------|-------|--------------|------|--------|
| **0** | Smart Chunker | Gemini 2.5 Pro | Extract logical topics with metadata | topics.json |
| **1a** | Content Director | Gemini 2.5 Pro | Generate intro/summary/content/example/quiz | content_sections.json |
| **1b** | Recap Director | Gemini 2.5 Pro | Generate memory (5 flashcards) + 5 recap_scene sections | recap_sections.json |
| **Merge** | Merge Step | Python | Deterministic merge of 1a + 1b | presentation.json |
| **1.5** | TTS Duration | Narakeet + Mutagen | Generate audio, measure actual duration | Updated presentation.json |
| **2** | Renderers | Various | Deterministic rendering | MP4 videos |
| **3** | Player | N/A | DUMB execution - follows JSON instructions | Video playback |

### Core Architectural Principles
- **PLAYER IS DUMB**: Executes JSON instructions without determining layout, timing, or pedagogy.
- **ONE PRIMARY ATTENTION LAYER AT A TIME**: Text or visuals are prominent, not both.
- **TEACH → THEN SHOW**: Narration explains, then visuals reinforce.
- **EVERYTHING IS TIMED**: All segments have precise, synchronized durations.
- **TWO-CHANNEL SEPARATION**: Narration is audio-only; `visual_content` is screen display only.
- **Fail-Fast Policy**: Strict fail-fast behavior with no fallbacks for critical components.

### Key Features and Design Decisions
- **Split Director Architecture**: Divides LLM responsibilities into `Content Director` (main content) and `Recap Director` (memory, recap scenes) to improve LLM compliance.
- **TTS Duration Measurement**: Utilizes Narakeet for audio generation and Mutagen for precise duration measurement, updating the presentation JSON.
- **Targeted Retry Strategy**: Implements specific retry mechanisms for LLM calls to handle structural and semantic errors.
- **JSON Repair Pre-Validation**: Includes steps to clean and repair LLM-generated JSON before validation.
- **Display Directives**: Each narration segment includes explicit `display_directives` for controlling `text_layer`, `visual_layer`, and `avatar_layer`. Text must hide before complex visuals appear.
- **Mandatory Sections**: `intro`, `summary`, `memory` (5 flashcards), and 5 `recap_scene_N` sections (each with 100+ word `video_prompt`) are strictly required.
- **Avatar Rules**: Specific visibility and sizing rules for avatars based on section type.
- **Manim Hard Rule**: Manim renderer requires `manim_scene_spec` for every visual beat.
- **Two-Channel Content Separation**: `narration.segments[].text` for TTS, `visual_content` for on-screen display.
- **Renderer Hardening**: Strict validation for Remotion (JSON-only), and WAN/Video (minimum word count, no vague phrases).
- **Schema Validation**: Uses `schemas/presentation_v1.3.schema.json` for strict JSON Schema validation.
- **Renderer Decision Rules**: Director LLM dynamically selects renderers: Manim for math/physics, Video (WAN) for biology/chemistry/recap, Remotion for intro/summary/memory/quiz motion graphics.
- **Khan Academy-Style Theme**: Dark theme with specific color codes and fonts (Lato, Caveat).
- **Merge Step Enhancement**: Converts 5 separate `recap_scene_N` sections from LLM output into one `recap` section for player compatibility.
- **Status Callbacks**: Real-time job progress updates during pipeline execution.

### Technical Stack
- **Backend**: Python Flask API.
- **Frontend**: Vanilla HTML5/JavaScript.
- **LLM Gateway**: OpenRouter.
- **TTS**: Narakeet.
- **Video Editing**: MoviePy.

## External Dependencies
- **OpenRouter**: Provides access to various LLMs (Gemini 2.5 Flash, Gemini 2.5 Pro, Claude Sonnet).
- **Narakeet API**: Text-to-Speech service.
- **Kie.ai API (WAN)**: Conceptual video generation.
- **Datalab API**: PDF to Markdown conversion.
- **Flask**: Python web framework.
- **Flask-CORS**: Handles Cross-Origin Resource Sharing for Flask.
- **MoviePy**: Python library for video editing.
- **OpenAI Python Client**: Used for OpenRouter gateway.
- **Tenacity**: General-purpose retry library.
- **Mutagen**: Python module to handle audio metadata and measure duration.

## V1.4 Test Status (2025-12-23)

### Math Calculus Test - PASS
- **Sections**: 10 (intro, summary, 5 content, example, memory, recap)
- **Renderers**: Remotion (4), Manim (5), Video/WAN (1)
- **Content Director**: 35,273 tokens, $0.29
- **Recap Director**: 8,522 tokens, $0.06
- **Total Cost**: $0.38
- **Duration**: 413s
- **Display Validation**: PASS
- **Manim Specs**: All 5 manim sections have valid manim_scene_spec

### Issues Verified Fixed
- **ISS-106**: Renderers now executing (videos folder populated)
- **ISS-107**: Duration normalization for memory/recap segments
- **ISS-108**: Control character repair in JSON (newlines/tabs)
- **ISS-109**: Manim section validation requires manim_scene_spec with objects/animation_sequence
- **ISS-110**: Token accumulation across retries working correctly