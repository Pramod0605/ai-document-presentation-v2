# AI Animated Education

---
## VERSION LOCK - V1.5 BASELINE
**Locked Date**: December 28, 2025  
**Commit**: 74eff4688a15535e0082c2f80afceb9124dd7bb1  
**Status**: STABLE - Ready for optimization phase

### Locked Components (Do Not Modify Without Approval)

**Pipeline Architecture:**
- V1.5 pipeline flow: Chunker → SectionPlanner → NarrationWriter → VisualSpecArtist → RendererSpec → MemoryAgent → RecapAgent → MergeStep → TTS → RendererExecutor → Player
- Schema validation: v1.3
- All LLM agent prompts in `core/prompts/`

**Player V2 System:**
- 7 section types: intro, summary, content, example, quiz, memory, recap
- Layer architecture: Background (L0), Content (L1), Avatar (L2)
- LaTeX/MathJax rendering with placeholder preservation
- Progressive text reveal synced to narration
- Beat video playlist with segment-based transitions
- Video looping when narration > video length

**Renderers:**
- Manim: Claude Sonnet 4.5 for code generation
- WAN 2.6: 15-sec max, narration-duration based (capped at 15s)
- Image display: .image-container, .content-image, .image-caption

**Audio/Video Sync:**
- TTS-measured durations drive all timing
- Recap beats use narration segment durations
- Player loops videos during long narration segments

**Visual Display:**
- Header: "Simple Lecture" logo + dynamic section title
- Content layer: 70% width, no borders
- Avatar layer: 55% width, 85% height, floating right
- Video layer: 65% width, hides content during playback

---

## Overview
This project is a **Deterministic Educational Film Engine** designed to convert PDF chapters into pedagogically structured, animated explanation videos with synchronized narration. Its core purpose is to automate the creation of high-quality, engaging educational content by leveraging AI-driven animation and narration to enhance learning.

## User Preferences
The user wants an iterative development process. The agent should prioritize clear, concise, and accurate communication. Before making any major architectural changes or introducing new dependencies, the agent must ask for explicit approval. The user prefers detailed explanations for complex technical decisions. The agent should ensure that all code is well-documented and follows best practices for maintainability and readability.

## System Architecture
The system operates on a V1.5 pipeline, an evolution designed to automate the creation of educational films.

### Core Architectural Principles
- **PLAYER IS DUMB**: The player executes JSON instructions without determining layout, timing, or pedagogy.
- **ONE PRIMARY ATTENTION LAYER AT A TIME**: Text or visuals are prominent, not both.
- **TEACH → THEN SHOW**: Narration explains, then visuals reinforce.
- **EVERYTHING IS TIMED**: All segments have precise, synchronized durations.
- **TWO-CHANNEL SEPARATION**: Narration is audio-only; `visual_content` is screen display only.
- **Fail-Fast Policy**: Strict fail-fast behavior with no fallbacks for critical components.

### V1.5 Pipeline Flow
The process is orchestrated through a series of specialized agents:
`Chunker` → `SectionPlanner` → `[per-section: NarrationWriter → VisualSpecArtist → RendererSpec]` → `MemoryAgent` → `RecapAgent` → `MergeStep` → `TTS` → `RendererExecutor` → `Player`

This architecture uses multiple smaller agents to reduce LLM output size and isolate failures.

### V1.5 Optimized Pipeline (December 2025)
Cost optimization variant reducing LLM calls by ~50%:
`Chunker` → `SectionPlanner` → `[per-section: ContentCreator → RendererSpec]` → `SpecialSectionsAgent` → `MergeStep` → `TTS||ManimCodeGen` → `Renderers`

**Combined Agents:**
- **ContentCreator**: Combines NarrationWriter + VisualSpecArtist (2→1 call per section)
  - Outputs coupled narration + visual_beats + segment_enrichments
  - V3 persona styles: "Namaste students" intro, quizmaster for quiz
  - Detects Q&A pairs, marks display_format: "flashcard"
- **SpecialSectionsAgent**: Combines MemoryAgent + RecapAgent (2→1 call)
  - Memory: 3 flashcards with mnemonic ("3 Keys to Remember")
  - Recap: 5 video prompts with storyteller persona, Indian context

**Parallel Execution:**
- TTS generation runs in parallel with Manim code generation
- ThreadPoolExecutor with max_workers=2

**Enforcements:**
- Section order validation: intro → summary → content(s) → memory → recap (hard fail on intro/summary)
- Avatar visibility: Never "hide", always "show" or "gesture_only"

**Files:**
- `core/pipeline_v15_optimized.py`: Optimized pipeline function
- `core/agents/content_creator.py`: Combined content agent
- `core/agents/special_sections.py`: Combined memory+recap agent
- `core/prompts/content_creator_system_v1.5.txt`: ContentCreator prompt
- `core/prompts/special_sections_system_v1.5.txt`: SpecialSections prompt

### Guardrails
- **Presentation Schema Immutability**: Validation against v1.3 schema.
- **Player Code Freeze**: No changes to the `player/` directory.
- **Two-Channel Separation**: `narration.text` must not equal `visual_content`.
- **Display Directive Mutual Exclusion**: `text_layer` and `visual_layer` cannot both be 'show'.
- **Renderer Spec Required**: Non-none renderers require a corresponding specification.
- **Idempotent Agent Retries**: Agents are pure functions to ensure consistent retries.

### Narration Sync Architecture
Narration segments are written, visual beats and display directives are created, then merged. TTS generates audio and actual durations are measured and updated, which the player then uses for timing and display directives.

### Content Display Fidelity (ISS-160)
The system now threads Block IDs through the pipeline to ensure narration segments accurately correspond to source content blocks, preventing "blank slide" issues. `SmartChunker` outputs `block_id`, `VisualSpecArtist` uses `source_block_ids`, and a post-processor enhances visual content types based on block ID lookup.

### UI/UX Decisions
- Layer Architecture: Layer 0 (Background), Layer 1 (Content), Layer 2 (Avatar - always visible).
- `player.js` supports `avatar always-visible` and `width_percent`.

### Enhanced Content Display (ISS-180)
The `renderFormattedContent()` function in `player.js` handles various display types including quiz cards, memory sections, bullet lists, paragraphs, and mixed content. This includes styling and proper rendering for different pedagogical elements.

### Display & Playback Fixes (ISS-181 to ISS-184)
- **ISS-181**: Markdown sanitizer strips markdown syntax from verbatim text.
- **ISS-182**: Summary sections prioritize LLM-generated learning objectives (bullet_points).
- **ISS-183**: Avatar visibility is ensured during Manim/video playback.
- **ISS-184**: Manim audio sync is fixed by setting playback rate to 1.0 and explicit audio play calls.

### Content Display Fixes (ISS-185 to ISS-187)
- **ISS-185**: `fitContentToContainer()` dynamically scales font to prevent text overflow.
- **ISS-186**: Summary sections are filtered to display only level 1 bullet points.
- **ISS-187**: A `contentRendered` flag prevents duplicate content boxes by gating the legacy renderer.

### LaTeX & Media Fixes (ISS-194 to ISS-200)
- **ISS-194**: LaTeX rendering preserved in `sanitizeMarkdown()` via placeholder extraction/restoration.
- **ISS-195**: `typesetMath()` properly waits for MathJax startup and targets contentBox element.
- **ISS-196**: Beat video playlist in `renderRecap()` sequences WAN videos with narration segments.
- **ISS-197**: Pipeline populates `visual_beats[].video_asset` after WAN video generation (3 locations).
- **ISS-198**: Image display support with CSS styling (.image-container, .content-image, .image-caption).
- **ISS-199**: WAN video sync with narration - upgraded to WAN 2.6 (15-sec max), pipeline uses narration segment durations (capped at 15s), player loops videos when narration exceeds video length.
- **ISS-200**: Recap video path population fix - `_render_visual_beats()` now supports `return_all_paths=True` to return all generated video paths (handles dry-run, skip-wan, and production modes). Recap sections using `video_prompts` now correctly set `topic["_recap_video_paths"]` for player sequencing.

### Player V2 Architecture
A complete rewrite of the player with a clean architecture and enhanced features.
- **Chroma Keying**: Canvas-based green screen removal for avatar video.
- **Section Title Display**: Prominent, styled titles for each section (hidden for intro).
- **Progressive Text Reveal**: Content reveals in sync with narration.
- **Content Splitting**: Large content auto-paginates and transitions with narration.
- **Visual Borders**: Styled borders for content and video layers.
- **Media Path Resolution**: Helper function `resolveMediaPath()` for audio/video paths.
- **7 Section Types Supported**: Intro, summary, content, example, quiz, memory, recap.
- **Avatar Positioning**: Configurable for intro (centered) and other sections (right side, overlapping content).
- **Layout Updates**: Content layer is 70% width without borders; avatar layer is 55% width, 85% height, floating over content; video layer is 65% width and hides content during Manim playback.

### Player V2 Enhancements (ISS-188 to ISS-193)
- **ISS-188**: Added header bar with logo and presentation title.
- **ISS-189**: Ported dev mode panel with sliders for avatar scale, chroma threshold, content width, and segment list.
- **ISS-190**: Filters "Thinking..." and gesture-only segments from visual display.
- **ISS-191**: Detects and filters `[pause X seconds]` from visual display.
- **ISS-192**: Verified Manim/narration sync with `playbackRate=1.0`.
- **ISS-193**: Reviewed WAN video prompts for detailed cinematic quality.

### LLM Outputs Browser
Allows browsing and inspecting all LLM outputs per job for prompt quality assessment, including agent outputs, renderer prompts, source content, and pipeline traces, accessible via a split-pane modal in the dashboard.

### Analytics Tracking
Tracks per-job analytics including pipeline status, duration, LLM phase breakdown (model, tokens, cost), content metrics, renderer metrics, and TTS metrics. Data is saved in `analytics.json` and displayed in a dashboard modal.

### Retry Failed Jobs
Enables resuming failed jobs from the point of failure. The system determines the failed section, loads existing artifacts, and continues the pipeline from that point.

### Key System Specifications
- **Display Requirements**: Detailed in `docs/display_requirements.md`, covering display summary, layer architecture, and ASCII diagrams for 7 section types.
- **V1.5 Requirements**: Defined in `docs/v1.5_requirements.json`, covering phases, requirements, agent contracts, JSON schemas, and guardrails.
- **LLM Agent Reference**: `docs/display_requirements.md` outlines all 7 agents with their inputs, outputs, and prompt files.
- **Manim Code Generation**: Claude Sonnet 4.5 is used for Python code output and validation.

## External Dependencies
-   **OpenRouter**: Provides access to various LLM models (Gemini 2.5 Pro, Gemini 2.5 Flash, Claude Sonnet).
-   **Edge TTS**: Default Text-to-Speech service (Microsoft, en-IN-PrabhatNeural).
-   **Narakeet API**: Fallback for Text-to-Speech.
-   **Kie.ai API (WAN)**: Used for video generation.
-   **Datalab API**: Handles PDF to Markdown conversion.
-   **Flask/Flask-CORS**: Python web framework.
-   **Mutagen**: Library for measuring audio duration.
-   **MoviePy**: Used for video editing.
-   **Renderers**: Manim, Remotion, and WAN (Kie.ai) for visual rendering.