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

### 2. System Requirements (for Manim)
Manim requires system-level dependencies:

**Windows:**
```bash
# Install Chocolatey, then:
choco install miktex ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install texlive-full ffmpeg
```

**macOS:**
```bash
brew install --cask mactex
brew install ffmpeg
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

**Key packages:**
- `manim` - Mathematical animation engine
- `edge-tts` - Microsoft Edge TTS (free)
- `pyttsx3` - Offline TTS fallback
- `moviepy` - Video processing
- `rembg` - Background removal for images


### 4. Start Server
```bash
python api/app.py
```

### 5. Access Dashboard
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

## Technical Documentation
For deep-dive architecture and implementation details:

*   **[V2.5 Director Pipeline Spec](docs/v2.5_Director_Pipeline_Technical_Doc.md):** Full architecture, Data Flow, and Agent Logic.
*   **[Player V2.5 Technical Spec](player_v2_technical.md):** Browser rendering logic, Compliance Matrix, and Features.


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

## Server Operations & Maintenance

### 1. Docker Management
- **Start/Rebuild Server**: `docker compose up -d --build`
- **Stop Server**: `docker compose down`
- **Restart Server**: `docker compose restart`

### 2. Code Updates
- **Update to latest code**: `git pull`
- **Apply updates and restart**:
  ```bash
  git pull
  docker compose up -d --build
  ```

### 3. Monitoring & Logs
- **View live logs**: `docker compose logs -f`
- **Check specific service**: `docker compose logs -f api`
- **Monitor logs on server**: `./view_logs.bat` (Local) or `tail -f debug.log` (Server)

### 4. Utility Scripts
- **Validate `presentation.json` Content**:
  `python verify_job_content.py <JOB_ID>` (Detailed Director Bible compliance check)
- **Check Job Status**:
  `python check_job.py <JOB_ID>`
- **Reset Stuck Jobs**:
  `python reset_jobs.py` (Resets all "processing" jobs to "failed" in index)
- **Manual Job Fix**:
  `python fix_job_status.py` (Manually update/fix specific job entries)
- **Analyze Job Fidelity**:
  `python scripts/deep_fidelity_analysis.py <JOB_ID>`

## Production Utilities

Scripts are provided (Windows PowerShell) to help manage the production server without needing manual SSH commands:

| Script | Description | Usage |
|--------|-------------|-------|
| `production_login.ps1` | Open full SSH shell | `.\production_login.ps1` |
| `production_logs.ps1` | View live server logs | `.\production_logs.ps1` |
| `production_docker_shell.ps1` | Open bash inside container | `.\production_docker_shell.ps1` |
| `production_inspect_job.ps1` | View job files/content | `.\production_inspect_job.ps1 961f56e8 [file.json]` |

### Sanity Check
Access the visual sanity checker for any job:
`http://69.197.145.4:5005/sanity_check.html?job=<JOB_ID>`

## License

MIT License
