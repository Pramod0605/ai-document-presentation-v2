# AI Animated Education - Phase 1 (v1.3)

## Overview
This project develops a **Deterministic Educational Film Engine** that transforms PDF chapters into pedagogically structured, animated explanation videos with synchronized narration. It uses a **3-pass LLM architecture** with strict role separation. Version 1.3 introduces display_directives for layer control, mandatory section validation, and avatar rules per section type.

## User Preferences
The user wants an iterative development process. The agent should prioritize clear, concise, and accurate communication. Before making any major architectural changes or introducing new dependencies, the agent must ask for explicit approval. The user prefers detailed explanations for complex technical decisions. The agent should ensure that all code is well-documented and follows best practices for maintainability and readability.

### NON-NEGOTIABLE RULES (CRITICAL)
1. **Before proposing ANY solution**, the agent MUST check:
   - `attached_assets/` folder for specification documents (especially LLM brain prompts)
   - `docs/llm_output_requirements_v1.3.json` for definitive LLM output specification (v1.3)
   - `replit.md` for documented architecture and decisions
   - Existing prompt files in `core/prompts/` (v1.3 prompts)
   - `issues.json` for tracked problems and their agreed solutions
2. The agent must NOT assume or invent solutions - all proposals must reference documented specifications.
3. Nothing is a "solution" until the user explicitly agrees.
4. When in doubt, ASK the user - do not proceed with assumptions.
5. The LLM is the "brain" - timing, durations, and creative decisions come from LLM output, not from post-processing calculations.
6. **ALL LLM OUTPUTS MUST CONFORM TO `docs/llm_output_requirements_v1.3.json` OR FAIL** - this is non-negotiable. There are NO FALLBACKS. Missing required fields = generation failure.
7. **Player is a DUMB display layer** - it consumes LLM output without modification. No duration calculations, no content fallbacks, no graceful degradation.
8. **Issue Tracking First** - Any issue noticed MUST be logged to `issues.json` with full details BEFORE proposing any solution.
9. **Upstream/Downstream Impact Analysis** - Before code changes, verify upstream and downstream components are not affected. If they are, include those fixes in the proposal and ask for user approval.
10. **No Deviation Without Approval** - No deviations from the initial goal. Any code changes must be approved by the user first.

## System Architecture (v1.3)

### Pipeline Architecture (v1.3 Deterministic Film Engine)

| Pass | Phase | Model | Role | Output |
|------|-------|-------|------|--------|
| **0** | Chunker | Gemini 2.5 Flash | Pure preprocessing - split markdown | Chunked JSON |
| **1** | Director | Gemini 2.5 Pro | Pedagogy + structure + timing + display_directives | presentation.json (v1.3 schema) |
| **2** | Renderers | Various | Deterministic rendering (NO creative LLM decisions) | MP4 videos |
| **3** | Player | N/A | DUMB execution - follows JSON instructions exactly | Video playback |

### v1.3 Key Changes (NEW)
1. **display_directives** - Every narration segment MUST have:
   - `text_layer`: show | hide | swap
   - `visual_layer`: show | hide | replace
   - `avatar_layer`: show | hide | gesture_only
   - **Rule**: Text MUST hide BEFORE complex visuals appear

2. **Mandatory Sections** (hard fail if missing):
   - intro
   - summary
   - memory (5 flashcards)
   - recap (5 scenes, 300-500 words)

3. **Avatar Rules per Section Type**:
   - **INTRO**: visible, center/overlay, ≥50% width
   - **CONTENT**: side position, 30-40% width
   - **EXAMPLE**: side small OR gesture_only
   - **QUIZ**: hidden or minimal
   - **MEMORY**: optional
   - **RECAP**: hidden (video only)

4. **Manim Hard Rule**: If renderer=manim, EVERY visual beat MUST include manim_scene_spec. Prose-only = HARD FAILURE.

5. **Two-Channel Content Separation** (ISS-056):
   - `narration.segments[].text` = TTS audio only, NEVER displayed on screen
   - `visual_content` = Screen display only (bullet_points, formula, labels)
   - Director extracts displayable content from source document into visual_content
   - Player aggregates segment visual_content for backward-compatible slide rendering

6. **Legacy Version Guard**:
   - Whitelist: `['', 'v1.0', 'v1.1', 'v1.2']` use narration text fallback
   - v1.3+ enforces visual_content, shows error placeholder if missing

### Core Principles (v1.3)
- **PLAYER IS DUMB**: Does NOT decide layout, timing, or pedagogy. Only executes JSON.
- **ONE PRIMARY ATTENTION LAYER AT A TIME**: Text OR visual - never together.
- **TEACH → THEN SHOW**: First explain with narration, THEN visualize.
- **EVERYTHING IS TIMED**: Every segment has duration_seconds, visuals align to timing.
- **TWO-CHANNEL SEPARATION**: narration=audio, visual_content=display (never mixed).

### Prompt Files (v1.3)
Located in `core/prompts/`:
- `director_system_v1.3.txt` / `director_user_v1.3.txt` (v1.3 with canonical JSON example)
- `director_retry_system.txt` / `director_retry_user.txt` (NEW - structure-repair-only retry)
- `chunker_system_v1.3.txt` / `chunker_user_v1.3.txt` (NEW v1.3)
- `manim_renderer_system_v1.2.txt` / `manim_renderer_user_v1.2.txt` (unchanged)
- `remotion_renderer_system_v1.2.txt` / `remotion_renderer_user_v1.2.txt` (unchanged)
- `video_renderer_system_v1.2.txt` / `video_renderer_user_v1.2.txt` (unchanged)

Backups stored in `core/prompts/v1.1_backup/` and `core/prompts/v1.2_backup/`.

### Schema Validation (v1.3 NEW)
JSON Schema validation runs FIRST, before Python semantic validation:
1. `schemas/presentation_v1.3.schema.json` - Strict JSON Schema
2. `core/schema_validator.py` - Validates against schema
3. If schema fails → retry with structure-repair prompt (max 2 retries)
4. If still fails → HARD FAIL (no fallbacks, no normalization repair)

### Director Retry Logic (v1.3 NEW)
- Max 2 retries with structure-repair-only prompts
- Retry prompt preserves narration/pedagogy, only fixes missing structure
- Hard fail after 2 retries (no fallbacks)

### Director Gemini Parameters (v1.3 NEW)
Optimized for deterministic output:
- `temperature: 0.2` (low creativity, high determinism)
- `top_p: 0.9`
- `max_tokens: 8192`

### Hard Fail Validation (v1.3)
The `core/hard_fail_validator.py` now enforces:

**Structure Checks:**
- missing_intro_section → FAIL
- missing_summary_section → FAIL
- missing_memory_section → FAIL
- missing_recap_section → FAIL

**Narration Checks:**
- content narration < 150 words → FAIL
- recap total narration < 300 or > 500 words → FAIL

**Display Directive Checks:**
- narration segment missing display_directives → FAIL
- text and visuals shown simultaneously → FAIL

**Avatar Checks:**
- intro avatar not visible or < 50% → FAIL
- recap avatar visible → FAIL

**Renderer Checks:**
- manim section without manim_scene_spec → FAIL

### Renderer Decision Rules (v1.3 - Director Decides)
| Renderer | Use Cases |
|----------|-----------|
| **Manim** | Formulas, equations, graphs, vectors, geometry, numeric physics |
| **Video (WAN)** | Biology processes, chemistry reactions, physical phenomena, recap storytelling |
| **Remotion** | intro/summary/memory/quiz sections (motion graphics, flashcard animations) |

**v1.3 Change:** Director decides renderer. Pipeline obeys. No Remotion→WAN collapse logic.
All sections (including intro/summary/memory) now have visual_beats assigned.

### Normalization Layer (v1.3 - PASS-THROUGH MODE)
The `normalize_director_output()` function in `core/pipeline_v12.py` is now PASS-THROUGH ONLY:
- Normalizes field NAMES only (narration_beats → narration.segments)
- Does NOT invent missing required fields
- Missing structure → schema validation failure → retry or hard fail

**v1.3 Change:** Normalization no longer back-fills or creates missing structures. If the Director LLM omits required fields, schema validation will fail and trigger retry logic.

### Technical Implementation
- **Backend**: Python Flask API.
- **Frontend**: Vanilla HTML5/JavaScript video player with dynamic layouts, subtitle synchronization, and chroma key avatar overlay.
- **LLM Pipeline**: 3-pass architecture via OpenRouter. Chunker → Director → Renderers.
- **Normalization**: Post-Director normalization layer converts LLM output variations to canonical schema.
- **Video Rendering**: Dual renderer system: Manim for mathematical animations, WAN/kie.ai for conceptual science videos.
- **Audio**: Narakeet TTS (Indian male voice "ravi") using streaming for short text and polling for long text.
- **Job Processing**: Asynchronous system for PDF/Markdown file submission, progress polling, and asset generation.
- **Fail-Fast Policy**: Strict fail-fast behavior with no fallbacks for critical components.

### Khan Academy-Style Theme
The player uses a blackboard-inspired dark theme:
- **Background**: #0a0a0a (near-black)
- **Fonts**: Lato (body text), Caveat (handwritten-style headers)
- **Primary Text**: #f0f0e8 (chalk-white)
- **Accent Green**: #00ff88 (headers, new button, step indicators)
- **Accent Cyan**: #00d4ff (active items, borders, progress bar)

### Data Structure (v1.3)
The `Presentation` JSON schema includes:
- `spec_version`: "v1.3"
- `title`, `subject`, `grade`
- `sections` array with:
  - `section_id`, `section_type`, `title`
  - `renderer`, `renderer_reasoning`
  - `layout` (content_zone, avatar_zone)
  - `narration`, `narration_segments` with `display_directives`
  - `visual_beats` with `manim_scene_spec` for manim sections

## Version History
- **v1.1**: Two-LLM architecture (Chunker + Director).
- **v1.2**: Three-pass architecture with specialized renderers. Adds analytics tracking.
- **v1.3**: Deterministic Film Engine. Adds display_directives, mandatory sections, avatar rules per section type. Hard-fail validation for missing sections.

## External Dependencies
- **OpenRouter**: For Gemini 2.5 Flash, Gemini 2.5 Pro, and Claude Sonnet LLMs.
- **Narakeet API**: Text-to-Speech service.
- **Kie.ai API (WAN)**: For conceptual video generation.
- **Datalab API**: For PDF to Markdown conversion.
- **Flask**: Backend web framework.
- **Flask-CORS**: Handles Cross-Origin Resource Sharing.
- **MoviePy**: Video editing tasks.
- **OpenAI Python Client**: For OpenRouter gateway.
- **Tenacity**: For API call retry logic.

## File Structure
```
core/
├── prompts/
│   ├── v1.1_backup/                  # v1.1 prompt backups
│   ├── v1.2_backup/                  # v1.2 prompt backups
│   ├── director_system_v1.3.txt      # v1.3 with canonical JSON example
│   ├── director_user_v1.3.txt        # v1.3
│   ├── director_retry_system.txt     # NEW - structure-repair-only retry
│   ├── director_retry_user.txt       # NEW - retry user template
│   ├── chunker_system_v1.3.txt       # NEW v1.3
│   ├── chunker_user_v1.3.txt         # NEW v1.3
│   ├── manim_renderer_system_v1.2.txt
│   ├── manim_renderer_user_v1.2.txt
│   ├── remotion_renderer_system_v1.2.txt
│   ├── remotion_renderer_user_v1.2.txt
│   ├── video_renderer_system_v1.2.txt
│   └── video_renderer_user_v1.2.txt
├── analytics.py             # Cost/time tracking per phase
├── pipeline_v12.py          # v1.3 pipeline (uses v1.3 prompts)
├── llm_client_v12.py        # v1.3 LLM calls
├── director_client.py       # NEW - Director client with retry logic
├── schema_validator.py      # NEW - JSON Schema validation
├── hard_fail_validator.py   # v1.3 validation rules
├── traceability.py          # Generation trace logging
└── latex_to_speech.py       # LaTeX→speakable text for TTS

schemas/
└── presentation_v1.3.schema.json  # NEW - Strict JSON Schema

docs/
├── llm_output_requirements_v1.3.json  # v1.3 specification (CURRENT)
├── llm_output_requirements.json       # v1.2 backup
└── llm_output_requirements_v1.1.json  # v1.1 backup
```
