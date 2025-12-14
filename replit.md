# AI Animated Education - Phase 1

## Project Overview

A production-grade AI pipeline that converts PDF chapters into topic-wise explanation videos with synchronized narration. The system uses LLM as the "Director" to make all creative decisions about content presentation.

## Architecture

- **Backend**: Python Flask API
- **Frontend**: Vanilla HTML5/JavaScript video player
- **LLM**: OpenRouter via Replit AI Integrations
- **Video**: Dual renderer system (Manim for math, WAN/kie.ai for science concepts)
- **Audio**: gTTS for Indian English narration

## Key Components

### API Layer (`api/app.py`)
- POST `/process_pdf` - Upload and process PDF files
- POST `/process_markdown` - Process markdown content
- GET `/health` - Health check
- GET `/player/*` - Serve video player

### Core Pipeline (`core/`)
- `llm_client.py` - OpenRouter LLM integration for content direction
- `pipeline.py` - Main orchestrator for the PDF-to-video flow
- `datalab_client.py` - PDF to Markdown conversion
- `renderer_executor.py` - Dispatch to appropriate renderer

### Renderers (`render/`)
- `manim/manim_runner.py` - Mathematical animations
- `wan/wan_client.py` - kie.ai API for conceptual videos

### TTS (`tts/generate_audio.py`)
- Indian English narration using gTTS

### Player (`player/`)
- YouTube-style HTML5 video player
- Subtitle sync, layout zones, dev mode

## Running the Project

The Flask server runs on port 5000. Access the player at `/player/index.html`.

## Environment Variables

- `KIE_API_KEY` - For WAN video generation (optional, uses placeholder if not set)
- `DATALAB_API_KEY` - For PDF conversion (optional, uses stub if not set)

## Dependencies

- flask, flask-cors
- gtts, moviepy
- openai, tenacity, requests
- python-dotenv
