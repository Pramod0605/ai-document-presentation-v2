# AI Animated Education Pipeline

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PIPELINE FLOW                                     │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │  1. UPLOAD       │
    │  (PDF/Markdown)  │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  2. PDF → MD     │  (Datalab API - if PDF)
    │  Conversion      │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  3. CHUNKING     │  Gemini 2.5 Flash
    │  (Flash LLM)     │  - Analyzes content structure
    │                  │  - Identifies topic boundaries
    │                  │  - Creates 2000-4000 word chunks
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  4. DIRECTOR     │  Gemini 2.5 Pro
    │  (Pro LLM)       │  - Generates presentation JSON per chunk
    │                  │  - Creates 5 section types:
    │                  │    • intro, summary, content, memory, recap
    │                  │  - Outputs manim_scene_spec for math
    │                  │  - Outputs visual_beats for WAN
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  5. MERGER       │  Combines all chunks
    │                  │  - Deduplicates sections
    │                  │  - Renumbers section IDs
    │                  │  - Creates unified presentation.json
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  6. FLASH        │  Gemini 2.5 Flash (Semantic Validator)
    │  VALIDATOR       │  - Checks visual beat quality
    │                  │  - PASS: specific equations, objects, motions
    │                  │  - FAIL: vague phrases like "animate smoothly"
    │                  │  - Strict mode for content/example sections
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  7. VISUAL       │  Python code
    │  COMPILER        │  - Translates manim_scene_spec → Manim code
    │                  │  - Compiles visual_beats → WAN prompts
    │                  │  - Structural validation (missing fields)
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────────────────────────────┐
    │  8. RENDERERS                            │
    │  ┌─────────────┐    ┌─────────────────┐  │
    │  │ MANIM       │    │ WAN (kie.ai)    │  │
    │  │ - Math      │    │ - Science       │  │
    │  │ - Equations │    │ - Concepts      │  │
    │  │ - Graphs    │    │ - Animations    │  │
    │  └─────────────┘    └─────────────────┘  │
    │         ↓                   ↓            │
    │    topic_X.mp4         topic_X.mp4       │
    └────────────────────┬─────────────────────┘
                         │
                         ▼
    ┌──────────────────┐
    │  9. TTS          │  Narakeet API (primary)
    │  Audio Gen       │  gTTS fallback
    │                  │  - Indian male voice (ravi)
    │                  │  → section_X.mp3
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │  10. PLAYER      │  HTML5 Video Player
    │                  │  - Syncs video + audio
    │                  │  - Section navigation
    │                  │  - Avatar overlay
    └──────────────────┘
```

## Key Files

| Component | File | Description |
|-----------|------|-------------|
| API | `api/app.py` | Flask endpoints, job management |
| Pipeline | `core/pipeline.py` | Main orchestrator |
| LLM Client | `core/llm_client.py` | OpenRouter calls, chunking logic |
| Flash Validator | `core/flash_validator.py` | Semantic quality check |
| Visual Compiler | `core/visual_compiler.py` | Spec → code translation |
| Manim Runner | `render/manim/manim_runner.py` | Manim execution |
| WAN Runner | `render/wan/wan_runner.py` | kie.ai API calls |
| TTS | `tts/generate_audio.py` | Audio generation |
| Player | `player/player.js` | Frontend video player |

## Presentation JSON Schema

```json
{
  "chapter_title": "string",
  "subject": "string",
  "grade": "string",
  "sections": [
    {
      "section_type": "intro|summary|content|example|memory|recap",
      "id": 1,
      "title": "Section Title",
      "renderer": "manim|wan_video",
      "narration": "Full narration text...",
      "visual_beats": [
        {
          "scene_setup": "...",
          "objects_and_properties": "...",
          "motion_sequence": "...",
          "labels_and_text": "...",
          "pedagogical_focus": "...",
          "manim_scene_spec": { ... }  // For renderer=manim
        }
      ]
    }
  ]
}
```

## Job Options

| Option | Default | Description |
|--------|---------|-------------|
| `dry_run` | false | Skip actual rendering, create markers |
| `skip_wan` | false | Skip WAN video generation |
| `skip_avatar` | false | Skip avatar overlay |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | LLM access (Flash + Pro) |
| `NARAKEET_API_KEY` | No | TTS (falls back to gTTS) |
| `KIE_API_KEY` | No | WAN video generation |
| `DATALAB_API_KEY` | No | PDF conversion |

## Two-Layer Validation

1. **Structural (Code)**: Missing fields = hard error
2. **Semantic (Flash LLM)**: Vague content = error for content sections

## Section Types

| Type | Purpose | Layout |
|------|---------|--------|
| intro | Warm introduction | center |
| summary | Learning objectives | side |
| content | Main teaching | side + video |
| example | Step-by-step worked example | side + video |
| memory | Flashcards/mnemonics | center |
| recap | Story-based review | image scenes |
