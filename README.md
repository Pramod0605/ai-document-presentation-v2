# AI Animated Education - Phase 1

A production-grade AI pipeline that converts PDF chapters into topic-wise explanation videos (MP4), synchronized with narration, and presented in a YouTube/Vimeo-style HTML player.

## Overview

This is a **narrated visual explanation engine**, not a slide system. The LLM acts as the Director and Brain, making all creative and technical decisions about how educational content should be presented.

## Features

- **PDF to Video Pipeline**: Upload a PDF chapter and get topic-wise explanation videos
- **LLM-Powered Direction**: AI decides topic breakdown, narration, visuals, and timing
- **Dual Renderer System**:
  - **Manim**: For mathematics, geometry, graphs, and formula derivations
  - **WAN (via kie.ai)**: For biology, physics, chemistry, and conceptual explanations
- **Text-to-Speech**: Indian English narration using gTTS
- **YouTube-style Player**: Professional video player with subtitles and avatar zones
- **Generation Tracing**: Complete audit trail of all LLM decisions

## How to Run Locally

1. **Start the server**:
   ```bash
   python api/app.py
   ```

2. **Access the player**:
   Open http://localhost:5000/player/index.html in your browser

3. **Upload content**:
   - Upload a PDF file, or
   - Use the sample content to see it in action

## How It Works

### PDF → Video Pipeline

1. **PDF Parsing**: PDF is converted to Markdown (Datalab integration)
2. **LLM Planning**: OpenRouter LLM analyzes content and creates a presentation plan
3. **Video Rendering**: Each topic is rendered using the appropriate engine (Manim or WAN)
4. **Audio Generation**: Narration is generated using gTTS with Indian English
5. **Player Assembly**: Videos, audio, and subtitles are synced in the HTML player

### JSON Control System

Everything is controlled by `presentation.json`:
- Chapter metadata (title, subject, grade)
- Topic breakdowns with renderer choices
- Layout configurations (content zone, avatar zone)
- Narration with timed segments
- Gesture hints for avatar

### Generation Trace

`generation_trace.json` stores:
- Full LLM prompts used
- Model information
- Renderer decisions with reasoning
- Timing decisions

## API Endpoints

- `POST /process_pdf` - Upload PDF and generate videos
- `POST /process_markdown` - Process markdown content directly
- `GET /health` - Health check
- `GET /player/*` - Serve the video player

## Environment Variables

- `KIE_API_KEY` - API key for WAN video generation (kie.ai)
- `DATALAB_API_KEY` - API key for PDF conversion (optional, uses stub if not set)

## Phase-1 Limitations

- **Avatar**: Placeholder only (no real AI avatar video)
- **Gestures**: Hints recorded but not rendered
- **PDF Parsing**: Stubbed conversion (real Datalab integration optional)
- **Video Duration**: WAN API may have limits on video length

## Phase-2 Roadmap

1. **Real AI Avatar**: Integration with D-ID or HeyGen for avatar generation
2. **Gesture System**: Sync avatar actions with content timing
3. **Interactive Dev Mode**: Drag-and-resize layout editor
4. **Real PDF Parsing**: Full Datalab integration
5. **Job Queue**: Background processing with progress tracking
6. **Caching**: Avoid regenerating unchanged content

## Project Structure

```
ai-animated-education-phase1/
├── api/
│   └── app.py              # Flask API server
├── core/
│   ├── datalab_client.py   # PDF to Markdown
│   ├── llm_client.py       # OpenRouter LLM integration
│   ├── pipeline.py         # Main orchestration
│   ├── renderer_executor.py # Renderer dispatch
│   └── prompts/
│       ├── system_prompt.txt
│       └── user_prompt.txt
├── render/
│   ├── manim/
│   │   └── manim_runner.py # Manim animation engine
│   └── wan/
│       ├── wan_client.py   # kie.ai API client
│       └── wan_runner.py   # WAN video runner
├── tts/
│   └── generate_audio.py   # gTTS audio generation
├── player/
│   ├── index.html          # Video player UI
│   ├── player.js           # Player JavaScript
│   └── assets/             # Generated content
├── examples/
│   ├── sample_markdown.md
│   └── sample_presentation.json
└── requirements.txt
```

## License

MIT License
