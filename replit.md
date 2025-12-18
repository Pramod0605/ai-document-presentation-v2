# AI Animated Education - Phase 1

## Overview
This project aims to develop a production-grade AI pipeline that transforms PDF chapters into pedagogically structured explanation videos with synchronized narration. The system leverages Large Language Models (LLMs) as a "Director" to make creative decisions regarding content presentation. The core purpose is to revolutionize educational content delivery by automating the creation of engaging and structured learning videos, targeting a broad market for digital education.

## User Preferences
The user wants an iterative development process. The agent should prioritize clear, concise, and accurate communication. Before making any major architectural changes or introducing new dependencies, the agent must ask for explicit approval. The user prefers detailed explanations for complex technical decisions. The agent should ensure that all code is well-documented and follows best practices for maintainability and readability.

## System Architecture

### Core Design
The system utilizes a two-model LLM pipeline via OpenRouter: Gemini 2.5 Flash for intelligent topic boundary detection (chunking) and Gemini 2.5 Pro for detailed visual and narration generation (direction). Content generation follows a mandatory 5-section pedagogical flow: Intro, Summary, Content, Memory, and Recap.

### Technical Implementation
- **Backend**: Python Flask API
- **Frontend**: Vanilla HTML5/JavaScript video player with a YouTube-style interface. The player supports dynamic layouts for different section types, subtitle synchronization, and chroma key avatar overlay.
- **LLM Pipeline**: Large documents are processed in chunks to avoid truncation. A Flash Chunker identifies logical topic boundaries, a Pro Director generates presentation JSON for each chunk, and a Merger combines outputs. A Flash LLM Validator semantically checks visual beat content.
- **Video Rendering**: A dual renderer system is employed: Manim for mathematical animations and WAN/kie.ai for conceptual science videos. The system supports per-beat video rendering.
- **Audio**: Narakeet TTS is primarily used with an Indian male voice (ravi), with gTTS as a fallback.
- **Job Processing**: An asynchronous job processing system allows for submitting PDF/Markdown files and polling for real-time progress updates. Each job creates a self-contained folder with all generated assets.

### UI/UX Decisions
The video player features a two-pane layout for video and content, with options for swapping their positions. Layouts adapt dynamically based on the `section_type` (e.g., `mode-center` for intros, `mode-side` for content). The dashboard provides a user interface for file uploads, subject/grade inputs, job status display, and playing completed videos.

### Data Structure
The `Presentation` JSON schema includes a `sections` array, where each section specifies its `section_type`, `id`, `title`, `renderer`, `explanation_plan`, `layout`, `narration`, `segments`, `flashcards`, and `recap_scenes`. `manim_scene_spec` is included within visual beats for Manim sections.

## External Dependencies
- **OpenRouter**: For accessing Gemini 2.5 Flash and Gemini 2.5 Pro LLMs.
- **Narakeet API**: Primary Text-to-Speech service for high-quality voice generation.
- **Google Text-to-Speech (gTTS)**: Fallback TTS service.
- **Kie.ai API (WAN)**: For generating conceptual videos.
- **Datalab API**: Used for PDF to Markdown conversion.
- **Flask**: Web framework for the backend API.
- **Flask-CORS**: Handles Cross-Origin Resource Sharing.
- **MoviePy**: Used for video editing tasks.
- **OpenAI Python Client**: For interacting with OpenAI services (though OpenRouter is primary LLM gateway).
- **Tenacity**: For retry logic in API calls.
- **Requests**: HTTP client library.
- **python-dotenv**: For managing environment variables.

## Recent Changes (Dec 18, 2025)
- **Image Handling Pipeline**: Added complete image extraction and display system
  - Extracts base64 images from markdown, saves with green background for chroma key
  - Images display with fade-in animation, synced to narration timing
  - Subtle hover effect (scale + shadow) for interactivity
  - LLM receives image placeholders (IMAGE_1, IMAGE_2) - not raw base64 data
  - Pipeline: PDF → markdown → extract images → strip base64 → send text to LLM
- **Section Type Rendering Rules**:
  - INTRO/SUMMARY/MEMORY: Text-only (no video/manim rendering)
  - CONTENT: Text + video/images with swapping
  - RECAP: Video-only (5 WAN scenes)
- **Image Display Layer**: New separate #image-display-layer in player, positioned alongside content without overlap
- **Male-Only Narration**: Narakeet "ravi" voice primary, gTTS UK male fallback

## Previous Changes (Dec 17, 2025)
- Upload Dialog Fix, TTS Voice Update, Avatar Positioning
- Memory Slide Enhancements (dual flashcard schema support)
- Recap Prompts (5 WAN video scenes)
- Display Mode field support in player

## Image Handling Architecture
```
PDF/Markdown → Datalab API → base64 images in markdown
    ↓
Extract images → Save with green background (rembg + PIL)
    ↓
Create placeholders → "IMAGE_1: filename.png"
    ↓
Send ONLY text to LLM (no base64 data)
    ↓
LLM assigns images with timing → {"image_ref": "IMAGE_1", "image_appear_time": 2.0}
    ↓
Player displays images synced to narration, one at a time, with hover effect
```

## Known Limitations
- **Validator Schema**: flash_validator.py still accepts old flashcard formats
- **Video Timing**: Animation durations may not perfectly match narration
- **Image Generation**: Currently extracts from source only - AI image generation not implemented