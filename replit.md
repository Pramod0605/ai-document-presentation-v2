# AI Animated Education

## Overview
This project is a **Deterministic Educational Film Engine** designed to convert PDF chapters into pedagogically structured, animated explanation videos with synchronized narration. Its core purpose is to automate the creation of high-quality, engaging educational content. The project aims to deliver a robust system capable of generating comprehensive educational films from static text, incorporating AI-driven animation and narration to enhance learning.

## User Preferences
The user wants an iterative development process. The agent should prioritize clear, concise, and accurate communication. Before making any major architectural changes or introducing new dependencies, the agent must ask for explicit approval. The user prefers detailed explanations for complex technical decisions. The agent should ensure that all code is well-documented and follows best practices for maintainability and readability.

## System Architecture
The system operates on a V1.5 pipeline, which is a significant architectural evolution from V1.4.

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

This architecture utilizes multiple smaller agents, each handling specific tasks, which reduces the LLM output size and isolates failures compared to the V1.4 monolithic approach.

### Guardrails
- **Presentation Schema Immutability**: Validation against v1.3 schema.
- **Player Code Freeze**: No changes to the `player/` directory.
- **Two-Channel Separation**: `narration.text` must not equal `visual_content`.
- **Display Directive Mutual Exclusion**: `text_layer` and `visual_layer` cannot both be 'show'.
- **Renderer Spec Required**: Non-none renderers require a corresponding specification.
- **Idempotent Agent Retries**: Agents are pure functions to ensure consistent retries.

### Narration Sync Architecture
1.  `NarrationWriter` outputs segments with estimated duration.
2.  `VisualSpecArtist` outputs `visual_beats` and `display_directives`.
3.  `MergeStep` combines segment data, visual content, and display directives.
4.  TTS generates audio and measures actual duration.
5.  `segment.duration_seconds` is updated with actual audio length.
6.  Player uses `segment.duration_seconds` for timing and `display_directives` for showing/hiding layers.

### ISS-160: Block Identifier Threading (Content Display Fidelity)
**Problem Solved**: "Blank slide" issue where narration segments exceeded source content blocks.

**Solution**: Block ID threading through the pipeline:
1. **SmartChunker** outputs `block_id` for each content block (paragraph, list, formula, etc.)
2. **VisualSpecArtist** receives content_blocks with block_id in prompt, outputs `source_block_ids` array per segment
3. **Post-processor** (`_enhance_visual_content_types`) uses block ID lookup instead of sequential mapping
4. **Multi-beat fidelity**: Multiple segments can reference the SAME block_id

**Key Files**:
- Schema: `schemas/v1.5/section_visuals.schema.json` - added `source_block_ids` field
- Prompts: `core/prompts/visual_spec_artist_user_v1.5.txt` - instructs LLM to output block IDs
- Pipeline: `core/pipeline_v15.py` - `_enhance_visual_content_types()` uses block lookup

**Example**: 5 narration segments explaining 3 content blocks:
```
Segment 1 → source_block_ids: [1] → paragraph data
Segment 2 → source_block_ids: [2] → paragraph data  
Segment 3 → source_block_ids: [3] → ordered_list data
Segment 4 → source_block_ids: [3] → ordered_list data (same block!)
Segment 5 → source_block_ids: [3] → ordered_list data (same block!)
```

### UI/UX Decisions
- Layer Architecture: Layer 0 for Background, Layer 1 for Content, Layer 2 for Avatar (always visible).
- `player.js` has been updated to support `avatar always-visible` and `width_percent`.

### ISS-179: Avatar Positioning (POSTPONED)
**Target Specs:**
- **Intro section**: 80% width, centered, bottom aligned - WORKING ✓
- **All other sections**: 810x455px at R:182px B:1px - POSTPONED

**Suspected root cause:** CSS layout constraints (60/40 split) conflicting with JavaScript positioning.

### ISS-180: Enhanced Content Display (COMPLETED - Dec 26, 2025)
**Implementation:**
- New `renderFormattedContent()` function in player.js handles all display types:
  - **Quiz cards**: Level 1 = question (styled card header), Level 2 = choices (A/B/C/D options)
  - **Memory sections**: Narration text displayed as key concept flashcard
  - **Bullet lists**: Proper indentation, styled bullet markers (●, ○, ◦, ◇)
  - **Paragraphs**: Border-left styled blocks with proper typography
  - **Mixed content**: Paragraph + bullets with divider

**Key files modified:**
- `player/jobs/75447304/player.js` - renderFormattedContent() function, loadSlide() integration
- `player/jobs/75447304/index.html` - CSS classes: .formatted-content-block, .quiz-card, .memory-concept-card, .formatted-bullet-list

**Critical fix:** Added `contentRendered` flag to prevent duplicate segment rendering when both ISS-180 and legacy blocks would create segments.

### ISS-181/182/183/184: Display & Playback Fixes (COMPLETED - Dec 27, 2025)
**Issues Fixed:**
1. **ISS-181**: Markdown sanitizer - Strips # headers and markdown syntax from verbatim_text before display
2. **ISS-182**: Summary section prioritization - Shows bullet_points (LLM-generated learning objectives) instead of verbatim_text (chapter headers with markdown)
3. **ISS-183**: Avatar visibility during video - Added CSS to ensure avatar stays visible during Manim/video playback
4. **ISS-184**: Manim audio sync - Set playback rate to 1.0 for Manim videos, added explicit audio.play() call

**Key changes:**
- `sanitizeMarkdown()` function handles all header variants (with/without space, trailing ###, underline-style)
- Summary sections use checkmark (✓) markers with blue gradient styling
- Avatar CSS: `opacity: 1 !important; visibility: visible !important;` during video modes
- Manim videos sync properly with narration audio at 1.0x playback rate

### ISS-185/186/187: Content Display Fixes (COMPLETED - Dec 27, 2025)
**Issues Fixed:**
1. **ISS-185**: Text overflow - Added `fitContentToContainer()` dynamic font scaler (65%-100% range with line-height adjustment)
2. **ISS-186**: Summary sub-bullets - Filtered to level 1 only (main bullets, no sub-bullets in summary sections)
3. **ISS-187**: Duplicate content boxes - Fixed `contentRendered` flag to gate legacy renderer after paragraph/ordered_list/formula rendering

**Key changes:**
- `fitContentToContainer()` scales font progressively until content fits, falls back to scroll
- Summary rendering: `bulletPoints.filter(bp => !bp.level || bp.level === 1)`
- `contentRendered = true` set in all direct-rendering blocks to prevent duplicate DOM elements

### Player V2 Architecture (COMPLETED - Dec 27, 2025)
**Complete rewrite** of the player with clean architecture and enhanced features.

**Key Files:**
- `player/player_v2.html` - Clean HTML structure with canvas-based avatar
- `player/player_v2.css` - Responsive layout with visual borders
- `player/player_v2.js` - Unified renderer with progressive reveal

**Features Implemented:**
1. **Chroma Keying** - Canvas-based green screen removal for avatar video
   - `renderChromaFrame()` processes video frames in real-time
   - Pixel-by-pixel green detection with configurable threshold
   - Falls back to placeholder if video unavailable

2. **Section Title Display** - Prominent title at top of each section
   - Gradient background with accent border
   - Hidden for intro sections

3. **Progressive Text Reveal** - Content reveals in sync with narration
   - Elements reveal one-by-one as audio plays
   - First item always visible immediately
   - Falls back to show-all if no audio

4. **Content Splitting** - Large content auto-paginates
   - Detects overflow and splits into timed pages
   - Pages transition as narration progresses
   - Skips splitting if no audio timing available

5. **Visual Borders** - Content and video layers have styled borders
   - Subtle glow effect with rounded corners

6. **Media Path Resolution** - `resolveMediaPath()` helper
   - Handles audio/ and videos/ subfolders
   - Works with job-specific paths

**7 Section Types Supported:**
- intro, summary, content, example, quiz, memory, recap

**Avatar Positioning:**
- Intro: 85% width, centered
- Other sections: 55% width, right side (overlapping content)

**Layout Updates (Dec 27, 2025):**
- Content layer: 70% width, no borders (seamless look)
- Avatar layer: 55% width, 85% height, floats over content
- Video layer: 65% width, hides content layer during Manim playback
- Removed visible division between content and avatar areas
- Added video-mode class management to reset layer states between slides

### ISS-188 to ISS-193: Player V2 Enhancements (Dec 27, 2025)
**Issues Fixed:**
1. **ISS-188**: Added header bar with "Simply Learn" logo (left) and presentation title from JSON (center)
2. **ISS-189**: Ported dev mode panel with avatar scale, chroma threshold, content width sliders + segment list
3. **ISS-190**: Added filter for "Thinking..." and gesture-only segments (hidden placeholders maintain ID alignment)
4. **ISS-191**: Added [pause X seconds] detection - pauses are filtered from visual display (already in audio)
5. **ISS-192**: Verified Manim/narration sync - both generated from same segment durations, playbackRate=1.0
6. **ISS-193**: Reviewed WAN video prompts - detailed cinematic prompts with proper durations

**Key Changes:**
- New `#header-bar`, `#dev-panel` DOM elements and CSS
- `isThinkingSegment()` function filters unwanted visual content while preserving segment ID alignment
- Dev panel toggle with 'D' key, sliders for real-time adjustments
- `updateDevInfo()` shows current slide info and clickable segment list

### LLM Outputs Browser (Dec 27, 2025)
**Feature**: Browse and inspect all LLM outputs per job for prompt quality assessment.

**What's Available:**
- **Agent Outputs** (artifacts/): SmartChunker, SectionPlanner, NarrationWriter, VisualSpecArtist outputs
- **Renderer Prompts** (render_prompts.json): All Manim/WAN video generation prompts
- **Source Content** (source_markdown.md): Original input from PDF conversion
- **Pipeline Trace** (generation_trace.json): Full execution trace with LLM calls

**Implementation:**
- `api/app.py`: `/job/<id>/llm-outputs` lists available files, `/job/<id>/llm-outputs/<path>` fetches content
- `player/dashboard.html`: "LLM Outputs" button opens split-pane modal with file tree + content viewer
- Custom renderers for each artifact type (narration segments, visual beats, content blocks, planner sections)

**Usage:**
- Click "LLM Outputs" button on any job in dashboard
- Browse file tree on left, click to view formatted content on right
- Color-coded by type: green=narration, purple=visuals, blue=chunker, cyan=planner, orange=renderer

### Analytics Tracking (Dec 27, 2025)
**Feature**: Per-job analytics tracking and dashboard display.

**What's Tracked:**
- Pipeline status, duration, and timestamps
- LLM phase breakdown: model, tokens, cost, duration per agent call
- Content metrics: sections, segments, slides, section types
- Renderer metrics: Manim videos, WAN videos, static slides
- TTS metrics: provider, voice, duration, character count

**Implementation:**
- `core/analytics.py`: Enhanced AnalyticsTracker with TTSMetrics, RendererMetrics, ContentMetrics
- `core/pipeline_v15.py`: `_save_analytics()` writes analytics.json on job completion/failure
- `api/app.py`: `/job/<job_id>/analytics` endpoint fetches stored data
- `player/dashboard.html`: "Analytics" button opens modal with metrics display

**Usage:**
- Click "Analytics" button on any completed/failed job in dashboard
- Modal shows: status, duration, LLM cost, token counts, content summary, TTS info, phase breakdown table

### Key System Specifications
- **Display Requirements**: Detailed in `docs/display_requirements.md`, including display summary, layer architecture, and ASCII diagrams for 7 section types (intro, summary, content, example, quiz, memory, recap).
- **V1.5 Requirements**: Defined in `docs/v1.5_requirements.json`, covering phases, requirements, agent contracts, JSON schemas, and guardrails.
- **LLM Agent Reference**: `docs/display_requirements.md` outlines all 7 agents with their inputs, outputs, and prompt files.
- **Manim Code Generation**: Claude Sonnet 4.5 is used for Python code output and validation.

## External Dependencies
-   **OpenRouter**: Provides access to various LLM models (Gemini 2.5 Pro, Gemini 2.5 Flash, Claude Sonnet).
-   **Edge TTS**: Free Microsoft Text-to-Speech service, default with en-IN-PrabhatNeural Indian male voice.
-   **Narakeet API**: Used as a fallback for Text-to-Speech.
-   **Kie.ai API (WAN)**: Used for video generation.
-   **Datalab API**: Handles PDF to Markdown conversion.
-   **Flask/Flask-CORS**: Python web framework for the backend.
-   **Mutagen**: Library for measuring audio duration.
-   **MoviePy**: Used for video editing.
-   **Renderers**: Manim, Remotion, and WAN (Kie.ai) are integrated for visual rendering.