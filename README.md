# AI Document Presentation - V2.5 Director Pipeline

Transform educational documents into rich, animated video presentations with AI Avatar narration, Manim animations, and synchronized visual content.

## Overview

The **V2.5 Director Pipeline** is a production-grade AI system that converts Markdown documents into multi-layer animated presentations. It uses LLM-powered "Director" logic to intelligently partition content, generate narration, and create synchronized visual animations.

## V2.5 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    V2.5 Director Pipeline                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌────────────────┐   │
│  │ Markdown │───▶│ Smart        │───▶│ Partition      │   │
│  │ Document │    │ Partitioner  │    │ Director (LLM) │   │
│  └──────────┘    └──────────────┘    └────────────────┘   │
│                                              │             │
│                         ┌────────────────────┘             │
│                         ▼                                  │
│              ┌────────────────────┐                       │
│              │   presentation.json │                       │
│              │   (18 sections)     │                       │
│              └────────────────────┘                       │
│                         │                                  │
│         ┌───────────────┼───────────────┐                 │
│         ▼               ▼               ▼                 │
│  ┌──────────┐   ┌──────────────┐  ┌───────────┐         │
│  │ Manim    │   │ TTS Audio    │  │ AI Avatar │         │
│  │ Generator│   │ (our_tts/    │  │ Generator │         │
│  │ (LLM)    │   │  edge_tts)   │  │           │         │
│  └──────────┘   └──────────────┘  └───────────┘         │
│         │               │               │                 │
│         ▼               ▼               ▼                 │
│  ┌──────────┐   ┌──────────────┐  ┌───────────┐         │
│  │  .mp4    │   │   .wav/.mp3  │  │   .mp4    │         │
│  │  Videos  │   │    Audio     │  │  Avatar   │         │
│  └──────────┘   └──────────────┘  └───────────┘         │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

## Key Features

### V2.5 Director Pipeline
- **Smart Partitioning**: Chunks large documents (55K+ chars) for parallel LLM processing
- **Section-Aware Structure**: 18 distinct section types per V2.5 Director Bible
- **Narration Segments**: LLM generates educator-style explanations with timing
- **Multi-Renderer Support**: Manim for math, Cards for text, Avatar for presenter

### Renderers
| Renderer | Use Case | Output |
|----------|----------|--------|
| `manim` | Mathematical formulas, graphs, animations | Python → MP4 |
| `text_card` | Definitions, bullet points | SVG/HTML layer |
| `avatar` | AI presenter narrating content | MP4 video |
| `flashcard_set` | Memory/quiz sections | Interactive cards |

### TTS Providers
- **our_tts**: Custom TTS API (69.197.145.4:8000) - Recommended
- **edge_tts**: Microsoft Edge TTS (free, network-dependent)
- **narakeet**: Premium Indian voices (paid)
- **pyttsx3**: Offline Windows TTS (fallback)

## Quick Start

### 1. Clone & Configure
```bash
git clone https://github.com/Pramod0605/ai-document-presentation-v2.git
cd ai-document-presentation-v2
cp .env_example .env
# Edit .env with your API keys
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start Server
```bash
python api/app.py
```

### 4. Access Dashboard
Open [http://localhost:5000/dashboard](http://localhost:5000/dashboard)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | LLM via OpenRouter (Claude/Gemini) |
| `DATALAB_API_KEY` | PDF to Markdown conversion |
| `OUR_TTS_BASE_URL` | Custom TTS API endpoint |
| `OUR_TTS_API_KEY` | Custom TTS API key |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/submit_job` | POST | Submit new presentation job |
| `/job/<id>/status` | GET | Get job processing status |
| `/regenerate_manim/<id>` | POST | Regenerate Manim code |
| `/job/<id>/avatar_status` | GET | Avatar generation progress |

## Project Structure

```
ai-document-presentation-v2/
├── api/app.py                    # Flask API server
├── core/
│   ├── pipeline_unified.py       # V2.5 Pipeline orchestrator
│   ├── unified_director_generator.py
│   ├── partition_director_generator.py
│   ├── tts_duration.py           # TTS providers
│   ├── agents/
│   │   ├── manim_code_generator.py
│   │   └── avatar_generator.py
│   └── prompts/
│       ├── director_partition_prompt.txt
│       └── manim_*.txt
├── player/
│   ├── dashboard.html            # Job management UI
│   ├── player_v2.html            # Presentation player
│   └── jobs/                     # Generated presentations
└── v2.5_Director_Bible.md        # Pipeline specification
```

## Pipeline Modes

| Mode | Description |
|------|-------------|
| `v2.5-partition-conquer` | Full V2.5 Director with smart partitioning |
| `v2-unified-single` | Legacy single-chunk Director |
| `v1.5-legacy` | Original pipeline (deprecated) |

## Job Output

Each job creates:
```
player/jobs/{job_id}/
├── presentation.json    # All sections with narration
├── manim_code/          # Python Manim scripts
│   └── section_*.py
├── videos/              # Rendered MP4 animations
├── audio/               # TTS audio files
├── avatars/             # AI avatar videos
└── avatar_status.json   # Avatar generation progress
```

## License

MIT License
