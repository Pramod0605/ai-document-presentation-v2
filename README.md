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

## Deployment

### Docker Deployment (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Pramod0605/ai-document-presentation-v2.git
   cd ai-document-presentation-v2
   ```

2. **Configure Environment Variables**:
   - Copy `.env_example` to `.env`:
     ```bash
     cp .env_example .env
     ```
   - Open `.env` and replace the dummy keys with your actual API keys.

3. **Build and Run**:
   ```bash
   docker-compose up --build -d
   ```

4. **Access the Dashboard**:
   Open [http://localhost:5000/dashboard](http://localhost:5000/dashboard) in your browser.

### Manual Run (Local)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the server**:
   ```bash
   python api/app.py
   ```

## Job Concurrency

The system is configured to handle **4 parallel jobs** by default. 
- If you submit more than 4 jobs, they will be **queued** and processed automatically as workers become available.
- This ensures server stability while allowing for high-throughput video generation.

## Environment Variables

The following variables must be configured in your `.env` file:

- `OPENROUTER_API_KEY`: API key for LLM generation (via OpenRouter).
- `DATALAB_API_KEY`: API key for PDF/Document conversion (via Datalab).
- `KIE_API_KEY`: API key for WAN video generation and AI video services (via kie.ai).

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
