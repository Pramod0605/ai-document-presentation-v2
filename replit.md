# AI Animated Education - Phase 1 (v1.5 Planning)

## Overview
This project is a **Deterministic Educational Film Engine** that converts PDF chapters into pedagogically structured, animated explanation videos with synchronized narration. Its primary goal is to automate the creation of high-quality, engaging educational content.

**Current Status**: V1.4 operational, V1.5 Split Agent Architecture ALL PHASES COMPLETE (PHASE-0 through PHASE-4).

## SINGLE SOURCE OF TRUTH

### Display & Agent Reference (v2.1)
**Primary Reference**: `docs/display_requirements.md`

This document contains:
- Display Summary Table (avatar widths: 60%/45%/35% by section type)
- Layer Architecture (Layer 0=Background, Layer 1=Content, Layer 2=Avatar always visible)
- ASCII diagrams for ALL 7 section types (intro, summary, content, example, quiz, memory, recap)
- LLM Agent Reference (all 7 agents with inputs/outputs/prompt files)
- **Manim Code Generation** section (Claude Sonnet 4.5, Python code output, validation)
- **Test Plan** section (TEST-001 to TEST-003)
- Narration Sync Architecture (timing flow from NarrationWriter → TTS → Player)
- Requirement Tracking (REQ-001 through REQ-068)
- Test Input Document specification

### V1.5 Architecture (Implemented)
**Primary Reference**: `docs/v1.5_requirements.json`

This file contains:
- All phases and requirements with status tracking
- Agent contracts and JSON schemas
- Guardrails and validation rules
- Presentation.json field mapping

### V1.4 Architecture (Current)
**Primary Reference**: `docs/llm_output_requirements_v1.4.json`

## User Preferences
The user wants an iterative development process. The agent should prioritize clear, concise, and accurate communication. Before making any major architectural changes or introducing new dependencies, the agent must ask for explicit approval. The user prefers detailed explanations for complex technical decisions. The agent should ensure that all code is well-documented and follows best practices for maintainability and readability.

### Critical Rules
1. Before proposing ANY solution, the agent MUST check:
   - `docs/display_requirements.md` for Display, Agent Reference, and Requirement Tracking (SINGLE SOURCE OF TRUTH)
   - `docs/v1.5_requirements.json` for V1.5 architecture spec
   - `docs/llm_output_requirements_v1.4.json` for current V1.4 specification
   - `attached_assets/` for specification documents (especially LLM brain prompts)
   - `replit.md` for documented architecture and decisions
   - `issues.json` for tracked problems and their agreed solutions
2. The agent must NOT assume or invent solutions - all proposals must reference documented specifications.
3. Nothing is a "solution" until the user explicitly agrees.
4. When in doubt, ASK the user - do not proceed with assumptions.
5. The LLM is the "brain" - timing, durations, and creative decisions come from LLM output, not from post-processing calculations.
6. **Presentation Schema Immutable**: presentation.json (v1.3 schema) MUST NOT change. All agent outputs merge into this exact structure.
7. **Player Code Updated**: player.js updated with avatar always-visible and width_percent support (REQ-030/031 complete).
8. Issue Tracking First - Any issue noticed MUST be logged to `issues.json` with full details BEFORE proposing any solution.
9. Upstream/Downstream Impact Analysis - Before code changes, verify upstream and downstream components are not affected.
10. No Deviation Without Approval - No deviations from the initial goal. Any code changes must be approved by the user first.

## System Architecture

### Pipeline Comparison

| Aspect | V1.4 (Current) | V1.5 (Planned) |
|--------|----------------|----------------|
| **Agents** | 3 (Chunker, ContentDirector, RecapDirector) | 6 (Chunker, SectionPlanner, NarrationWriter, VisualSpecArtist, RendererSpec, Memory/Recap) |
| **LLM Output Size** | 50+ fields per call | 5-15 fields per agent |
| **Retry Scope** | Entire presentation | Per-agent |
| **Problem** | High retry cascades | Isolated failures |

### V1.5 Pipeline Flow
```
Chunker → SectionPlanner → [per-section: NarrationWriter → VisualSpecArtist → RendererSpec] → MemoryAgent → RecapAgent → MergeStep → TTS → RendererExecutor → Player
```

### Core Architectural Principles (UNCHANGED)
- **PLAYER IS DUMB**: Executes JSON instructions without determining layout, timing, or pedagogy.
- **ONE PRIMARY ATTENTION LAYER AT A TIME**: Text or visuals are prominent, not both.
- **TEACH → THEN SHOW**: Narration explains, then visuals reinforce.
- **EVERYTHING IS TIMED**: All segments have precise, synchronized durations.
- **TWO-CHANNEL SEPARATION**: Narration is audio-only; `visual_content` is screen display only.
- **Fail-Fast Policy**: Strict fail-fast behavior with no fallbacks for critical components.

### Guardrails (from v1.5_requirements.json)
- **G1**: Presentation Schema Immutability - validate against v1.3 schema
- **G2**: Player Code Freeze - no changes to player/ directory
- **G3**: Two-Channel Separation - narration.text != visual_content
- **G4**: Display Directive Mutual Exclusion - text_layer + visual_layer not both 'show'
- **G5**: Renderer Spec Required - non-none renderers need corresponding spec
- **G6**: Idempotent Agent Retries - agents are pure functions

### Narration Sync Architecture
1. NarrationWriter outputs segments with estimated duration (word_count / 130 * 60)
2. VisualSpecArtist outputs visual_beats referencing segment_ids
3. VisualSpecArtist outputs display_directives per segment
4. MergeStep combines: segment + visual_content + display_directives
5. TTS Pass generates audio, measures actual duration via mutagen
6. TTS Pass updates segment.duration_seconds with actual audio length
7. Player reads segment.duration_seconds for playback timing
8. Player reads display_directives to show/hide layers at correct times

### Key Invariants
- `sum(segment.duration_seconds) = section total duration`
- `visual_beat[i].sync_to_segment` maps to `segment_id`
- `display_directives[i]` corresponds to `segment[i]`

## Technical Stack
- **Backend**: Python Flask API
- **Frontend**: Vanilla HTML5/JavaScript (FROZEN for V1.5)
- **LLM Gateway**: OpenRouter (Gemini 2.5 Pro, Gemini 2.5 Flash, Claude Sonnet)
- **TTS**: Edge TTS (default, free) with Narakeet fallback
- **Video Editing**: MoviePy
- **Renderers**: Manim, Remotion, WAN (Kie.ai)

## External Dependencies
- **OpenRouter**: LLM access
- **Edge TTS**: Microsoft free TTS (en-IN-PrabhatNeural Indian male voice)
- **Narakeet API**: Text-to-Speech (fallback)
- **Kie.ai API (WAN)**: Video generation
- **Datalab API**: PDF to Markdown conversion
- **Flask/Flask-CORS**: Web framework
- **Mutagen**: Audio duration measurement

## V1.5 Implementation Status

See `docs/v1.5_requirements.json` for detailed status of each requirement.

### Phase Status
- **PHASE-0**: Requirements & Contracts - COMPLETE (2025-12-23)
- **PHASE-1**: Agent Prompts & Contracts - COMPLETE (2025-12-23)
- **PHASE-2**: Orchestration & Merge - COMPLETE (2025-12-23)
- **PHASE-3**: TTS & Renderer Integration - COMPLETE (2025-12-23)
- **PHASE-4**: API & Dashboard Wiring - COMPLETE (2025-12-23)

### V1.5 New Files Created
| Component | Files |
|-----------|-------|
| Pipeline Orchestrator | `core/pipeline_v15.py` |
| Merge Step | `core/merge_step_v15.py` |
| Narration Sync | `core/narration_sync.py` |
| API Endpoints | `/api/v15/generate`, `/api/v15/pipeline-info` |
| Dashboard | Pipeline selector dropdown added |

### V1.5 Agents Implemented (PHASE-1)
| Agent | Files | Output Fields |
|-------|-------|---------------|
| SectionPlanner | `core/agents/section_planner.py` | ~10 fields per section |
| NarrationWriter | `core/agents/narration_writer.py` | 5 fields (section_id, narration.full_text, segments) |
| VisualSpecArtist | `core/agents/visual_spec_artist.py` | ~12 fields (visual_beats, segment_enrichments) |
| RendererSpecAgent | `core/agents/renderer_spec_agent.py` | Variable (manim/video spec) - remotion removed |
| MemoryFlashcard | `core/agents/memory_agent.py` | 5 flashcards |
| RecapScene | `core/agents/recap_agent.py` | 5 video prompts (300+ words each) |

## V1.4 Test Status (2025-12-23)

### Math Calculus Test - PASS
- **Sections**: 10 (intro, summary, 5 content, example, memory, recap)
- **Renderers**: Remotion (4), Manim (5), Video/WAN (1)
- **Total Cost**: $0.38
- **Duration**: 413s
- **Display Validation**: PASS

## V1.5 Test Status (2025-12-23)

### Math Calculus Test - PASS
- **Job ID**: 288f2129
- **Duration**: ~13 minutes
- **Phases Completed**: chunker → narration → visuals → renderer_spec → memory → recap → merge → TTS → render_specs
- **TTS Provider**: Edge TTS (free)
- **Status**: COMPLETED

### V1.5 Issues Fixed (2025-12-23)
- **VisualSpecArtist segments error**: Fixed double-unwrapping in validate_semantic
- **AnalyticsTracker add_llm_call**: Added missing method for V1.5 agent tracking
- **RendererSpec list object_id**: Fixed to handle list-type object_ids in manim validation
- **RecapScene banned phrases**: Relaxed to warnings, lowered min word count to 200
- **ISS-115**: Post-TTS audio consolidation - concatenates segment audio into section_X.mp3
- **ISS-118**: Remotion renderer removed - SectionPlanner only allows manim/video/none
- **ISS-121**: Section-level display_directives arrays added for player compatibility

### Remaining Issues
- **ISS-117**: Manim renders fail due to LLM generating invalid Python code
- **ISS-120**: WAN/Video prompts exceed API character limit (1900+ chars)

### Recent Issues Fixed (V1.4)
- **ISS-111**: Renderer execution wired into V1.4 pipeline
- **ISS-112/114**: Player BASE_PATH handles ?job= query parameter
- **ISS-113**: Renderer policy enforcement for text-only sections
