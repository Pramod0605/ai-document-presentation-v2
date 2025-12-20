# AI Animated Education - Phase 1 (v1.2)

## Overview
This project develops an AI pipeline to transform PDF chapters into pedagogically structured, animated explanation videos with synchronized narration. It uses a **3-pass LLM architecture** with role-pure separation of concerns. Version 1.2 introduces specialized renderers and analytics tracking.

## User Preferences
The user wants an iterative development process. The agent should prioritize clear, concise, and accurate communication. Before making any major architectural changes or introducing new dependencies, the agent must ask for explicit approval. The user prefers detailed explanations for complex technical decisions. The agent should ensure that all code is well-documented and follows best practices for maintainability and readability.

### NON-NEGOTIABLE RULES (CRITICAL)
1. **Before proposing ANY solution**, the agent MUST check:
   - `attached_assets/` folder for specification documents (especially LLM brain prompts)
   - `docs/llm_output_requirements.json` for definitive LLM output specification (v1.2)
   - `replit.md` for documented architecture and decisions
   - Existing prompt files in `core/prompts/` (v1.2 prompts)
   - `issues.json` for tracked problems and their agreed solutions
2. The agent must NOT assume or invent solutions - all proposals must reference documented specifications.
3. Nothing is a "solution" until the user explicitly agrees.
4. When in doubt, ASK the user - do not proceed with assumptions.
5. The LLM is the "brain" - timing, durations, and creative decisions come from LLM output, not from post-processing calculations.
6. **ALL LLM OUTPUTS MUST CONFORM TO `docs/llm_output_requirements.json` OR FAIL** - this is non-negotiable. There are NO FALLBACKS. Missing required fields = generation failure.
7. **Player is a DUMB display layer** - it consumes LLM output without modification. No duration calculations, no content fallbacks, no graceful degradation.

## System Architecture (v1.2)

### 3-Phase LLM Pipeline (Parse → Direct → Render)
The system uses a role-pure 3-phase architecture with clear separation of concerns:

| Phase | LLM | Model | Role | Output |
|-------|-----|-------|------|--------|
| **Parse** | Chunker | Gemini 2.5 Flash | Pure preprocessing - split markdown | Chunked JSON |
| **Direct** | Director | Gemini 2.5 Pro | Pedagogy + structure + timing + renderer choice | presentation.json (NO code) |
| **Render:Manim** | Manim Renderer | Claude 3.5 Sonnet | Math/physics visuals → scene spec | manim_scene_spec JSON |
| **Render:Remotion** | Remotion Renderer | Claude 3.5 Sonnet | Motion graphics → scene spec (when enabled) | remotion_scene_spec JSON |
| **Render:Video** | Video Renderer | Gemini 2.5 Pro | Biology/chemistry/recap → prompts | video_prompt JSON |

### Remotion Flag
- `use_remotion=False` (default): Remotion content routes to Video (WAN) instead
- `use_remotion=True`: Remotion renderer is used for motion graphics
- This allows development to proceed without Remotion installation

### Key Design Principles (v1.2)
- **Chunker**: Does NOT summarize, explain, or invent. Preserves wording exactly.
- **Director**: Decides pedagogy but does NOT generate renderer code.
- **Renderers**: Do NOT change narration or invent pedagogy. Pure execution.
- **Clean separation**: No mixed schemas, no self-review hallucinations.

### Prompt Files (v1.2)
Located in `core/prompts/`:
- `chunker_system_v1.2.txt` / `chunker_user_v1.2.txt`
- `director_system_v1.2.txt` / `director_user_v1.2.txt`
- `manim_renderer_system_v1.2.txt` / `manim_renderer_user_v1.2.txt`
- `remotion_renderer_system_v1.2.txt` / `remotion_renderer_user_v1.2.txt`
- `video_renderer_system_v1.2.txt` / `video_renderer_user_v1.2.txt`

Backups of v1.1 prompts stored in `core/prompts/v1.1_backup/`.

### Analytics Layer (NEW in v1.2)
The `core/analytics.py` module tracks per-phase metrics:
- **Time**: Start/end timestamps, duration_seconds
- **Cost**: Input tokens, output tokens, model pricing (USD)
- **Status**: Pass/fail per phase with error details

Model pricing stored for: Gemini 2.5 Flash, Gemini 2.5 Pro, Claude 3.5 Sonnet, GPT-4o.

### WAN Prompt Quality Validation (NEW in v1.2)
The `core/wan_prompt_validator.py` module validates video generation prompts:
- **Banned phrases**: Detects vague language like "something like", "kind of", "abstract representation"
- **Length check**: Minimum 50 chars for quality video generation
- **Quality scoring**: Checks for cinematographic direction (zoom, pan, fade, etc.)

Integrated into `renderer_executor.py` for automatic quality logging during v1.2 pipeline runs.

### Technical Implementation
- **Backend**: Python Flask API.
- **Frontend**: Vanilla HTML5/JavaScript video player with dynamic layouts, subtitle synchronization, and chroma key avatar overlay.
- **LLM Pipeline**: 3-pass architecture via OpenRouter. Chunker → Director → Renderers.
- **Video Rendering**: Dual renderer system: Manim for mathematical animations, Remotion for motion graphics, WAN/kie.ai for conceptual science videos.
- **Audio**: Narakeet TTS (Indian male voice "ravi") using streaming for short text and polling for long text. No fallback - failure results if API unavailable.
- **Job Processing**: Asynchronous system for PDF/Markdown file submission, progress polling, and asset generation into self-contained job folders.
- **Fail-Fast Policy**: Strict fail-fast behavior with no fallbacks for critical components.
- **Image Handling**: Extracts base64 images from markdown, processes them (green background for chroma key), creates placeholders for LLM, displays synced to narration.

### Renderer Decision Rules
| Renderer | Use Cases |
|----------|-----------|
| **Manim** | Math, vectors, geometry, graphs, derivations, numerical physics |
| **Remotion** | Intro motion graphics, summary animations, quiz displays, formula reveals |
| **Video (WAN)** | Biology processes, chemistry reactions, physical phenomena, recap storytelling |

### Symbolic Overlay Rule
During complex visuals, allow ONLY:
- Math symbols (a =, F =)
- Equation fragments
- Variable labels
- Step labels
- **Max 4 words. No sentences.**

### UI/UX Decisions
The video player features a two-pane layout (video and content) with position swapping and dynamic layout adaptation based on `section_type`. The dashboard supports file uploads, subject/grade inputs, job status display, and video playback. The player also supports per-beat display mode toggling (video-only, text-primary, video-primary).

### Khan Academy-Style Theme (Dec 2025)
The player uses a blackboard-inspired dark theme:
- **Background**: #0a0a0a (near-black)
- **Fonts**: Lato (body text), Caveat (handwritten-style headers)
- **Primary Text**: #f0f0e8 (chalk-white)
- **Accent Green**: #00ff88 (headers, new button, step indicators)
- **Accent Cyan**: #00d4ff (active items, borders, progress bar)
- **Yellow**: #ffff00 (flashcard highlights)
- **Orange**: #ff6b35 (alerts, quiz feedback)
- Original blue theme backed up in `backups/index.html.v1_blue` and `backups/player.js.v1_blue`

### Data Structure
The `Presentation` JSON schema includes a `sections` array, specifying `section_type`, `id`, `title`, `renderer`, `renderer_reasoning`, `layout`, `narration`, `narration_segments`, `visual_beats`, and renderer-specific specs (`manim_scene_spec`, `remotion_scene_spec`, or `video_prompts`).

## Version History
- **v1.1**: Two-LLM architecture (Chunker + Director). Director generated both pedagogy AND renderer specs.
- **v1.2**: Three-pass architecture with specialized renderers. Adds analytics tracking.

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
- **Requests**: HTTP client library.
- **python-dotenv**: For environment variables.

## File Structure
```
core/
├── prompts/
│   ├── v1.1_backup/         # Backed up v1.1 prompts
│   ├── chunker_system_v1.2.txt
│   ├── chunker_user_v1.2.txt
│   ├── director_system_v1.2.txt
│   ├── director_user_v1.2.txt
│   ├── manim_renderer_system_v1.2.txt
│   ├── manim_renderer_user_v1.2.txt
│   ├── remotion_renderer_system_v1.2.txt
│   ├── remotion_renderer_user_v1.2.txt
│   ├── video_renderer_system_v1.2.txt
│   └── video_renderer_user_v1.2.txt
├── analytics.py             # Cost/time tracking per phase
├── pipeline_v12.py          # v1.2 3-pass pipeline (CURRENT)
├── pipeline_v11.py          # v1.1 pipeline backup
├── pipeline.py              # Original pipeline (legacy)
├── llm_client_v12.py        # v1.2 3-pass LLM calls
├── llm_client.py            # v1.1 LLM calls (legacy)
├── hard_fail_validator.py   # Validation rules
├── traceability.py          # Generation trace logging
└── latex_to_speech.py       # LaTeX→speakable text for TTS

docs/
├── llm_output_requirements.json      # v1.2 specification (current)
└── llm_output_requirements_v1.1.json # v1.1 backup
```
