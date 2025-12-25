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

### UI/UX Decisions
- Avatar width is consistently 52% across all section types.
- Layer Architecture: Layer 0 for Background, Layer 1 for Content, Layer 2 for Avatar (always visible).
- `player.js` has been updated to support `avatar always-visible` and `width_percent`.

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