# AI Document Presentation - V2.5 Director Pipeline

Transform educational documents into rich, animated video presentations with AI Avatar narration, Manim animations, and synchronized visual content.

## Overview

The **V2.5 Director Pipeline** is a production-grade AI system that converts Markdown documents into multi-layer animated presentations. It uses LLM-powered "Director" logic to intelligently partition content, generate narration, and create synchronized visual animations.

---

## V2.5 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         V2.5 Director Pipeline - Full Workflow                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌────────────┐    ┌──────────────┐    ┌─────────────────┐                    │
│   │  Client    │───▶│   /submit_job │───▶│   Job Manager   │                    │
│   │  (Upload)  │    │   (POST)     │    │   (Async Queue) │                    │
│   └────────────┘    └──────────────┘    └────────┬────────┘                    │
│                                                   │                             │
│                ┌──────────────────────────────────┘                             │
│                ▼                                                                │
│   ┌────────────────────────────────────────────────────────────────┐           │
│   │                     PHASE 1: DOCUMENT PROCESSING                │           │
│   ├────────────────────────────────────────────────────────────────┤           │
│   │  ┌──────────┐    ┌──────────────┐    ┌────────────────┐       │           │
│   │  │ PDF/DOC  │───▶│ Datalab API  │───▶│  Markdown +    │       │           │
│   │  │ Upload   │    │ (Conversion) │    │  Images        │       │           │
│   │  └──────────┘    └──────────────┘    └───────┬────────┘       │           │
│   └──────────────────────────────────────────────┼────────────────┘           │
│                                                   │                             │
│                ┌──────────────────────────────────┘                             │
│                ▼                                                                │
│   ┌────────────────────────────────────────────────────────────────┐           │
│   │                     PHASE 2: LLM DIRECTOR                       │           │
│   ├────────────────────────────────────────────────────────────────┤           │
│   │  ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐  │           │
│   │  │ Smart        │───▶│ Partition       │───▶│ presentation │  │           │
│   │  │ Partitioner  │    │ Director (LLM)  │    │ .json        │  │           │
│   │  │ (55K chunks) │    │ (18 sections)   │    │ (V2.5 Spec)  │  │           │
│   │  └──────────────┘    └─────────────────┘    └──────┬───────┘  │           │
│   └─────────────────────────────────────────────────────┼─────────┘           │
│                                                          │                      │
│         ┌────────────────────────────────────────────────┘                      │
│         │                                                                       │
│         ▼                                                                       │
│   ┌────────────────────────────────────────────────────────────────┐           │
│   │                     PHASE 3: PARALLEL RENDERING                 │           │
│   ├────────────────────────────────────────────────────────────────┤           │
│   │                                                                 │           │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │           │
│   │  │   MANIM      │  │   WAN/KIE    │  │   TTS        │         │           │
│   │  │   Renderer   │  │   Video      │  │   Audio      │         │           │
│   │  │   (Math)     │  │   (Visuals)  │  │   (Voice)    │         │           │
│   │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │           │
│   │         │                 │                 │                  │           │
│   │         ▼                 ▼                 ▼                  │           │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │           │
│   │  │  videos/     │  │  videos/     │  │  audio/      │         │           │
│   │  │  topic_*.mp4 │  │  beat_*.mp4  │  │  *.mp3       │         │           │
│   │  └──────────────┘  └──────────────┘  └──────────────┘         │           │
│   │                                                                 │           │
│   └────────────────────────────────────────────────────────────────┘           │
│                                                                                 │
│         ┌───────────────────────────────────────────────────────────┐          │
│         │                     PHASE 4: AVATAR (Async)               │          │
│         ├───────────────────────────────────────────────────────────┤          │
│         │  ┌──────────────┐    ┌──────────────┐    ┌────────────┐  │          │
│         │  │ Narration    │───▶│ Avatar API   │───▶│ avatars/   │  │          │
│         │  │ Segments     │    │ (Kie.ai)     │    │ section_*  │  │          │
│         │  └──────────────┘    └──────────────┘    └────────────┘  │          │
│         └───────────────────────────────────────────────────────────┘          │
│                                                                                 │
│         ┌───────────────────────────────────────────────────────────┐          │
│         │                     OUTPUT: PLAYER                        │          │
│         ├───────────────────────────────────────────────────────────┤          │
│         │  /jobs/<job_id>/player_v2.html  ← Access presentation     │          │
│         │  /jobs/<job_id>/presentation.json                         │          │
│         │  /jobs/<job_id>/videos/                                   │          │
│         │  /jobs/<job_id>/avatars/                                  │          │
│         │  /jobs/<job_id>/audio/                                    │          │
│         └───────────────────────────────────────────────────────────┘          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

### V2.5 Director Pipeline
- **Smart Partitioning**: Chunks large documents (55K+ chars) for parallel LLM processing
- **Section-Aware Structure**: 18 distinct section types per V2.5 Director Bible
- **Narration Segments**: LLM generates educator-style explanations with timing
- **Multi-Renderer Support**: Manim for math, WAN for visuals, Avatar for presenter

### Renderers
| Renderer | Use Case | Output |
|----------|----------|--------|
| `manim` | Mathematical formulas, graphs, animations | Python → MP4 |
| `video` (WAN/Kie) | Visual storytelling, cinematic scenes | Prompt → MP4 |
| `text_card` | Definitions, bullet points | SVG/HTML layer |
| `avatar` | AI presenter narrating content | MP4 video |
| `flashcard_set` | Memory/quiz sections | Interactive cards |

### TTS Providers
- **our_tts**: Custom TTS API (69.197.145.4:8000) - Recommended
- **edge_tts**: Microsoft Edge TTS (free, network-dependent)
- **narakeet**: Premium Indian voices (paid)
- **pyttsx3**: Offline Windows TTS (fallback)

---

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

### 4. Start Server
```bash
python api/app.py
```
Server runs on `http://localhost:5000` (Docker maps to `5005` externally).

### 5. Access Dashboard
Open [http://localhost:5000/dashboard](http://localhost:5000/dashboard)

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | LLM via OpenRouter (Claude/Gemini) |
| `DATALAB_API_KEY` | PDF to Markdown conversion |
| `OUR_TTS_BASE_URL` | Custom TTS API endpoint |
| `OUR_TTS_API_KEY` | Custom TTS API key |
| `KIE_API_KEY` | Kie.ai Video/Avatar generation |

---

## API Endpoints Reference

### Job Submission & Status

#### `POST /submit_job`
Submit a new presentation job.

**Request (multipart/form-data):**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file` | File | Yes | - | PDF, DOC, DOCX, ODT, or MD file |
| `subject` | string | No | "General Science" | Subject area |
| `grade` | string | No | "9" | Grade level |
| `pipeline_version` | string | No | "v15_v2_director" | Pipeline: `v15_v2_director` |
| `tts_provider` | string | No | "edge_tts" | TTS: `our_tts`, `edge_tts`, `narakeet` |
| `video_provider` | string | No | "kie" | Video provider |
| `dry_run` | string | No | "false" | Skip actual rendering |
| `skip_wan` | string | No | "false" | Skip WAN video generation |
| `skip_avatar` | string | No | "false" | Skip avatar generation |
| `generation_scope` | string | No | "full" | Scope of generation |

**Response (200):**
```json
{
  "status": "queued",
  "job_id": "a1b2c3d4",
  "message": "Job submitted successfully",
  "player_url": "/jobs/a1b2c3d4/player_v2.html"
}
```

**Response (409 - Busy):**
```json
{
  "status": "busy",
  "message": "A job is already running. Please wait for it to complete.",
  "current_job_id": "existing_id"
}
```

---

#### `GET /job/<job_id>/status`
Get processing status for a job.

**Response (200):**
```json
{
  "job_id": "a1b2c3d4",
  "status": "processing",
  "progress": 45,
  "current_step": "Generating TTS Audio",
  "current_phase": "tts_generation",
  "status_message": "Processing section 5 of 18...",
  "steps_completed": 9,
  "total_steps": 20,
  "created_at": "2026-01-23T10:00:00Z",
  "started_at": "2026-01-23T10:00:05Z",
  "completed_at": null,
  "error": null,
  "progress_details": {...},
  "timings": {...}
}
```

**Status Values:**
| Status | Description |
|--------|-------------|
| `pending` | Job queued, waiting to start |
| `processing` | Job actively running |
| `completed` | Job finished successfully |
| `failed` | Job encountered an error |

---

#### `GET /jobs`
List all jobs with their status.

**Response (200):**
```json
{
  "jobs": [
    {
      "job_id": "a1b2c3d4",
      "type": "v15_v2_pipeline",
      "status": "completed",
      "progress": 100,
      "status_message": "Completed successfully",
      "created_at": "2026-01-23T10:00:00Z",
      "completed_at": "2026-01-23T10:15:00Z",
      "error": null,
      "params": {
        "subject": "Biology",
        "grade": "10",
        "dry_run": false
      }
    }
  ],
  "total": 1
}
```

---

#### `GET /job/<job_id>/analytics`
Get detailed analytics for a completed job.

**Response (200):**
```json
{
  "job_id": "a1b2c3d4",
  "has_analytics": true,
  "analytics": {
    "timings": {
      "total_duration_seconds": 890.5,
      "llm_phase": 120.3,
      "tts_phase": 45.2,
      "video_render_phase": 650.0
    },
    "token_usage": {
      "input_tokens": 50000,
      "output_tokens": 25000
    },
    "section_count": 18,
    "video_count": 15,
    "avatar_count": 18
  }
}
```

---

### Job Control

#### `POST /job/<job_id>/retry`
Retry a failed job from point of failure or fresh start.

**Response (200):**
```json
{
  "status": "started",
  "job_id": "a1b2c3d4",
  "message": "Retry started from section 12",
  "mode": "resume"
}
```

---

#### `POST /job/<job_id>/cancel`
Force cancel a running job.

**Response (200):**
```json
{
  "status": "cancelled",
  "job_id": "a1b2c3d4"
}
```

---

#### `POST /job/<job_id>/retry_phase`
Retry a specific phase for specific sections.

**Request (JSON):**
```json
{
  "phase": "manim_codegen",
  "section_ids": [3, 6, 11]
}
```

**Valid Phases:**
| Phase | Description |
|-------|-------------|
| `manim_codegen` | Regenerate Manim Python code |
| `manim_render` | Re-render Manim videos |
| `wan_render` | Re-render WAN/Kie videos |
| `avatar_generation` | Regenerate avatar videos |
| `tts_generation` | Regenerate TTS audio |

**Response (200):**
```json
{
  "status": "success",
  "phase": "manim_codegen",
  "result": {
    "sections_processed": [3, 6, 11],
    "success_count": 3
  }
}
```

---

### Avatar Generation

#### `POST /job/<job_id>/generate_avatar`
Trigger AI Avatar generation for a job.

**Response (200):**
```json
{
  "status": "queued",
  "message": "Avatar generation started"
}
```

**Response (409):**
```json
{
  "status": "already_running",
  "message": "Avatar generation in progress (Active Thread)"
}
```

---

#### `GET /job/<job_id>/avatar_status`
Get avatar generation progress.

**Response (200):**
```json
{
  "state": "processing",
  "message": "Generating avatar for section 5...",
  "progress": 35,
  "details": {
    "total_sections": 18,
    "completed_sections": 6,
    "failed_sections": []
  }
}
```

**State Values:**
| State | Description |
|-------|-------------|
| `idle` | Not started |
| `processing` | Generation in progress |
| `completed` | All avatars generated |
| `error` | Generation failed |
| `not_found` | Job doesn't exist |

---

#### `POST /job/<job_id>/regenerate_failed_avatars`
Regenerate only failed/missing avatars.

**Response (200):**
```json
{
  "status": "queued",
  "message": "Avatar retry started",
  "failed_sections_detected": [5, 12]
}
```

---

#### `POST /job/<job_id>/regenerate_avatar/<section_id>`
Regenerate avatar for a specific section.

**Response (200):**
```json
{
  "status": "queued",
  "section_id": "5"
}
```

---

### Manim Regeneration

#### `POST /regenerate_manim/<job_id>`
Regenerate Manim code for all manim sections.

**Response (200):**
```json
{
  "status": "success",
  "message": "Regenerated 5 Manim sections",
  "sections": [3, 6, 9, 12, 15]
}
```

---

### Metadata Repair

#### `POST /api/repair-metadata/<job_id>`
Surgically repair presentation.json by scanning for orphaned assets.

**Response (200):**
```json
{
  "status": "repaired",
  "updates": 12,
  "found_videos": ["topic_1.mp4", "topic_2.mp4"],
  "found_avatars": ["section_1_avatar.mp4"]
}
```

---

### Static File Serving

#### `GET /dashboard`
Serve the job management dashboard UI.

#### `GET /player/<filename>`
Serve player assets (legacy).

#### `GET /player_v2/<filename>`
Serve V2 player files.

#### `GET /jobs/<job_id>/`
Serve job-specific player (index.html).

#### `GET /jobs/<job_id>/<filename>`
Serve any file from job folder (videos, audio, avatars, etc.).

---

## Accessing Job Files

### Player Access
After a job completes, access the presentation player at:
```
http://<server>:<port>/jobs/<job_id>/player_v2.html
```

**Production Example:**
```
http://69.197.145.4:5005/jobs/a1b2c3d4/player_v2.html
```

### Sanity Check
Visual validation of presentation structure:
```
http://<server>:<port>/sanity_check.html?job=<job_id>
```

### Direct File Access
All job files are accessible via the `/jobs/<job_id>/` route:

| File | URL Pattern |
|------|-------------|
| Presentation JSON | `/jobs/<job_id>/presentation.json` |
| Analytics | `/jobs/<job_id>/analytics.json` |
| Source Markdown | `/jobs/<job_id>/source_markdown.md` |
| Videos | `/jobs/<job_id>/videos/<filename>.mp4` |
| Avatars | `/jobs/<job_id>/avatars/<filename>.mp4` |
| Audio | `/jobs/<job_id>/audio/<filename>.mp3` |
| Manim Code | `/jobs/<job_id>/manim_code/<filename>.py` |

---

## Job Output Structure

Each job creates the following folder structure:
```
player/jobs/{job_id}/
├── presentation.json       # All sections with narration, timing, visual specs
├── analytics.json          # Timing, token usage, render statistics
├── source_markdown.md      # Original document converted to markdown
├── source_document.pdf     # Backup of uploaded file
├── avatar_status.json      # Avatar generation progress
├── player_v2.html          # Self-contained player
├── player_v2.js            # Player logic
├── index.html              # Entry point
├── artifacts/              # LLM output artifacts
│   ├── 01_chunker.json
│   ├── 02_planner.json
│   └── ...
├── manim_code/             # Generated Manim Python scripts
│   └── section_*.py
├── videos/                 # Rendered video animations
│   ├── topic_*.mp4         # Per-section videos
│   └── topic_*_beat_*.mp4  # Per-beat videos (V2.5)
├── audio/                  # TTS audio files
│   └── section_*.mp3
├── avatars/                # AI avatar videos
│   └── section_*_avatar.mp4
└── images/                 # Extracted/processed images
    └── *.png
```

---

## Pipeline Modes

| Mode | Description |
|------|-------------|
| `v15_v2_director` | Full V2.5 Director with smart partitioning (default) |
| `v15` | V1.5 Optimized pipeline |
| `v14` | Split Director pipeline |

---

## Server Operations & Maintenance

### Docker Management
```bash
# Start/Rebuild Server
docker compose up -d --build

# Stop Server
docker compose down

# Restart Server
docker compose restart

# View live logs
docker compose logs -f
```

### Code Updates
```bash
git pull
docker compose up -d --build
```

### Production Deployment (Windows)
Use the provided PowerShell scripts:

| Script | Description |
|--------|-------------|
| `deploy_prod.ps1` | Pull latest code and restart container |
| `production_login.ps1` | SSH into production server |
| `production_logs.ps1` | View live production logs |
| `production_docker_shell.ps1` | Open bash inside container |
| `production_inspect_job.ps1 <job_id>` | Inspect job files on server |

---

## Technical Documentation

For deep-dive architecture and implementation details:
- **[V2.5 Director Bible](v2.5_Director_Bible.md):** The single source of truth for pipeline specification
- **[V2.5 Director Pipeline Spec](docs/v2.5_Director_Pipeline_Technical_Doc.md):** Full architecture, Data Flow, and Agent Logic
- **[Player V2.5 Technical Spec](player_v2_technical.md):** Browser rendering logic, Compliance Matrix, and Features

---

## Utility Scripts

| Script | Usage | Description |
|--------|-------|-------------|
| `verify_job_content.py` | `python verify_job_content.py <JOB_ID>` | Validate Director Bible compliance |
| `check_job.py` | `python check_job.py <JOB_ID>` | Quick job status check |
| `reset_jobs.py` | `python reset_jobs.py` | Reset stuck "processing" jobs to "failed" |
| `fix_job_status.py` | `python fix_job_status.py` | Manually fix job entries |
| `deep_fidelity_analysis.py` | `python scripts/deep_fidelity_analysis.py <JOB_ID>` | Analyze job quality |

---

## License

MIT License
