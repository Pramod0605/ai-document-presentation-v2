# AI Animated Education - Phase 1

## Overview
This project develops an AI pipeline to transform PDF chapters into pedagogically structured, animated explanation videos with synchronized narration. It uses Large Language Models (LLMs) as a "Director" for creative decisions, aiming to automate and revolutionize educational content delivery by creating engaging learning videos for the digital education market.

## User Preferences
The user wants an iterative development process. The agent should prioritize clear, concise, and accurate communication. Before making any major architectural changes or introducing new dependencies, the agent must ask for explicit approval. The user prefers detailed explanations for complex technical decisions. The agent should ensure that all code is well-documented and follows best practices for maintainability and readability.

### NON-NEGOTIABLE RULES (CRITICAL)
1. **Before proposing ANY solution**, the agent MUST check:
   - `attached_assets/` folder for specification documents (especially LLM brain prompts)
   - `replit.md` for documented architecture and decisions
   - Existing prompt files in `core/prompts/`
   - `issues.json` for tracked problems and their agreed solutions
2. The agent must NOT assume or invent solutions - all proposals must reference documented specifications.
3. Nothing is a "solution" until the user explicitly agrees.
4. When in doubt, ASK the user - do not proceed with assumptions.
5. The LLM is the "brain" - timing, durations, and creative decisions come from LLM output, not from post-processing calculations.

## System Architecture

### Core Design
The system employs a two-model LLM pipeline via OpenRouter: Gemini 2.5 Flash for topic chunking and Gemini 2.5 Pro for visual and narration generation. Content follows a mandatory 5-section pedagogical flow: Intro, Summary, Content, Memory, and Recap.

### Technical Implementation
- **Backend**: Python Flask API.
- **Frontend**: Vanilla HTML5/JavaScript video player with dynamic layouts, subtitle synchronization, and chroma key avatar overlay.
- **LLM Pipeline**: Processes large documents in chunks. A Flash Chunker identifies topic boundaries, a Pro Director generates presentation JSON, and a Merger combines outputs. A Flash LLM Validator semantically checks visual beat content.
- **Video Rendering**: Uses a dual renderer system: Manim for mathematical animations and WAN/kie.ai for conceptual science videos, supporting per-beat rendering.
- **Audio**: Narakeet TTS (Indian male voice "ravi") using streaming for short text and polling for long text. No fallback is implemented; failure results if the API is unavailable.
- **Job Processing**: Asynchronous system for PDF/Markdown file submission, progress polling, and asset generation into self-contained job folders.
- **Fail-Fast Policy**: Strict fail-fast behavior with no fallbacks for critical components like Datalab PDF→MD, Narakeet TTS, Manim, and WAN rendering.
- **Renderer Policy**: Enforces specific renderers per section type (TEXT-ONLY for intro, summary, memory; LLM Director choice for content/example; WAN for recap).
- **Image Handling**: Extracts base64 images from markdown, processes them (green background for chroma key), creates placeholders for LLM, and displays them synced to narration in the player.

### UI/UX Decisions
The video player features a two-pane layout (video and content) with position swapping and dynamic layout adaptation based on `section_type`. The dashboard supports file uploads, subject/grade inputs, job status display, and video playback. The player also supports per-beat display mode toggling (video-only, text-primary, video-primary).

### Data Structure
The `Presentation` JSON schema includes a `sections` array, specifying `section_type`, `id`, `title`, `renderer`, `explanation_plan`, `layout`, `narration`, `segments`, `flashcards`, `recap_scenes`, and `manim_scene_spec` for Manim sections.

## External Dependencies
- **OpenRouter**: For Gemini 2.5 Flash and Gemini 2.5 Pro LLMs.
- **Narakeet API**: Text-to-Speech service.
- **Kie.ai API (WAN)**: For conceptual video generation.
- **Datalab API**: For PDF to Markdown conversion.
- **Flask**: Backend web framework.
- **Flask-CORS**: Handles Cross-Origin Resource Sharing.
- **MoviePy**: Video editing tasks.
- **OpenAI Python Client**: For OpenAI services (though OpenRouter is primary LLM gateway).
- **Tenacity**: For API call retry logic.
- **Requests**: HTTP client library.
- **python-dotenv**: For environment variables.