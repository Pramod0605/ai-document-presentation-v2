# LLM Agent Requirements & Gap Analysis

## Document Purpose
This document serves as the comprehensive reference for all LLM agents in the V1.5 Split Agent Architecture, documenting:
- Prompt specifications and JSON output enforcement
- Storage architecture and artifact persistence
- Gap analysis between prompts and implementation
- Validation requirements

**Last Updated**: 2025-12-25

---

## Table of Contents
1. [Agent Overview](#agent-overview)
2. [Detailed Agent Specifications](#detailed-agent-specifications)
3. [Storage Architecture](#storage-architecture)
4. [Gap Analysis](#gap-analysis)
5. [Validation Flow](#validation-flow)

---

## Agent Overview

| # | Agent | Prompt File | Python File | JSON Enforced | Output Stored |
|---|-------|-------------|-------------|---------------|---------------|
| 1 | SmartChunker | `smart_chunker_system_v1.5.txt` | `core/llm_handler.py` | YES | In-memory → merge |
| 2 | SectionPlanner | `section_planner_system_v1.5.txt` | `core/agents/section_planner.py` | YES | In-memory → merge |
| 3 | NarrationWriter | `narration_writer_system_v1.5.txt` | `core/agents/narration_writer.py` | YES | In-memory → merge |
| 4 | VisualSpecArtist | `visual_spec_artist_system_v1.5.txt` | `core/agents/visual_spec_artist.py` | YES | In-memory → merge |
| 5 | RendererSpecAgent | `manim_spec_system_v1.5.txt`, `video_prompt_system_v1.5.txt` | `core/agents/renderer_spec_agent.py` | YES | In-memory → merge |
| 6 | MemoryFlashcard | `memory_flashcard_system_v1.5.txt` | `core/agents/memory_agent.py` | YES | In-memory → merge |
| 7 | RecapScene | `recap_scene_system_v1.5.txt` | `core/agents/recap_agent.py` | YES | In-memory → merge |
| 8 | ManimCodeGenerator | (inline prompt) | `core/agents/manim_code_generator.py` | NO (Python code) | In section.render_spec |

---

## Detailed Agent Specifications

### 1. SmartChunker

**Purpose**: First pass - extracts logical topics from markdown content

**Prompt File**: `core/prompts/smart_chunker_system_v1.5.txt`

**JSON Output Enforcement**:
```
You MUST output valid JSON with this exact structure:
```

**Output Schema**:
```json
{
  "source_topic": "Main subject of the document",
  "topics": [
    {
      "topic_id": "t1",
      "title": "Topic title",
      "concept_type": "process|definition|example|formula|theory|fact",
      "source_blocks": [1, 2, 3],
      "key_terms": ["term1", "term2"],
      "has_formula": false,
      "suggested_renderer": "manim|video|none"
    }
  ]
}
```

**Validation**: Structural (JSON parse) + Semantic (topic_id uniqueness)

**Storage**: Returned in-memory, passed to SectionPlanner

---

### 2. SectionPlanner

**Purpose**: Plans section structure from topics

**Prompt File**: `core/prompts/section_planner_system_v1.5.txt`

**JSON Output Enforcement**:
```
You MUST output ONLY valid JSON with this exact structure:
```

**Output Schema**:
```json
{
  "sections": [
    {
      "section_id": "section_1",
      "section_type": "intro|summary|content|example|quiz|memory|recap",
      "title": "Section Title",
      "source_topics": ["topic_id_1"],
      "learning_goals": ["What viewer will learn"],
      "suggested_renderer": "manim|video|none",
      "renderer_reasoning": "Why this renderer",
      "avatar_visibility": "required|optional",
      "avatar_position": "left|right|center",
      "avatar_width_percent": 52,
      "estimated_duration_seconds": 60
    }
  ]
}
```

**Validation**: 
- Structural: schema validation
- Semantic: section order (intro→summary→content→memory→recap), section_id sequential

**Storage**: In-memory as `blueprints[]`, passed to per-section agents

---

### 3. NarrationWriter

**Purpose**: Creates TTS narration scripts for one section

**Prompt File**: `core/prompts/narration_writer_system_v1.5.txt`

**JSON Output Enforcement**:
```
You MUST output ONLY valid JSON with this exact structure:
```

**Output Schema**:
```json
{
  "section_id": "section_X",
  "narration": {
    "full_text": "Complete narration...",
    "segments": [
      {
        "segment_id": 1,
        "text": "First segment...",
        "duration_seconds": 8.5,
        "gesture_hint": "pointing"
      }
    ]
  }
}
```

**Key Rules**:
- TWO-CHANNEL SEPARATION: Narration is AUDIO ONLY
- duration_seconds = word_count / 130 * 60 (estimated, TTS overrides)

**Validation**: 
- Structural: section_id, narration.full_text, segments required
- Semantic: segment_id sequential, word count within limits

**Storage**: In-memory as `narration_output`, added to `section_artifacts[]`

---

### 4. VisualSpecArtist

**Purpose**: Designs visual elements synchronized with narration segments

**Prompt File**: `core/prompts/visual_spec_artist_system_v1.5.txt`

**JSON Output Enforcement**:
```
You MUST output ONLY valid JSON with this exact structure:
```

**Output Schema**:
```json
{
  "section_id": "section_X",
  "visual_beats": [
    {
      "beat_id": "beat_1",
      "segment_id": 1,
      "visual_beat_type": "diagram|formula|process|video_clip|text_only|animation",
      "description": "Brief description",
      "symbolic_overlay": {
        "enabled": true,
        "content": ["Key", "Words"],
        "max_words": 4
      }
    }
  ],
  "segment_enrichments": [
    {
      "segment_id": 1,
      "visual_content": {
        "bullet_points": [{"level": 1, "text": "Key point"}],
        "formula": "LaTeX formula",
        "labels": ["Label1"]
      },
      "display_directives": {
        "text_layer": "show|hide|swap",
        "visual_layer": "show|hide|replace",
        "avatar_layer": "show|gesture_only"
      }
    }
  ]
}
```

**Key Rules**:
- ONE BEAT PER SEGMENT
- text_layer + visual_layer cannot BOTH be "show"
- avatar_layer: "hide" is NOT valid (avatar always visible)

**Validation**: 
- Structural: visual_beats array, segment_enrichments array
- Semantic: beat/segment count match, display directive rules

**Storage**: In-memory as `visuals_output`, added to `section_artifacts[]`

---

### 5. RendererSpecAgent

**Purpose**: Creates renderer-specific specs (Manim or Video prompts)

**Prompt Files**: 
- `core/prompts/manim_spec_system_v1.5.txt` (for manim)
- `core/prompts/video_prompt_system_v1.5.txt` (for video)

**JSON Output Enforcement**:
```
You MUST output ONLY valid JSON with this exact structure:
```

**Manim Output Schema**:
```json
{
  "section_id": "section_X",
  "renderer": "manim",
  "manim_scene_spec": {
    "objects": [
      {"id": "obj_1", "type": "Text|MathTex|...", "properties": {...}}
    ],
    "animation_sequence": [
      {"object_id": "obj_1", "animation": "Write|FadeIn|...", "timing": {...}}
    ]
  }
}
```

**Video Output Schema**:
```json
{
  "section_id": "section_X",
  "renderer": "video",
  "video_prompts": [
    {
      "beat_id": 1,
      "prompt": "300+ word detailed prompt...",
      "duration_seconds": 5.0,
      "style": "cinematic|documentary|educational|animated"
    }
  ]
}
```

**Validation**: 
- Structural: renderer field, corresponding spec present
- Semantic: object_id references valid, no banned phrases

**Storage**: In-memory as `render_spec`, added to `section_artifacts[]`

---

### 6. MemoryFlashcard

**Purpose**: Creates exactly 5 flashcards for memory section

**Prompt File**: `core/prompts/memory_flashcard_system_v1.5.txt`

**JSON Output Enforcement**:
```
You MUST output ONLY valid JSON with this exact structure:
```

**Output Schema**:
```json
{
  "section_id": "memory",
  "section_type": "memory",
  "title": "Remember This!",
  "avatar_layout": {
    "position": "right",
    "width_percent": 52
  },
  "flashcards": [
    {
      "flashcard_id": 1,
      "front": "Question?",
      "back": "Answer",
      "category": "Definition|Formula|Process|Example|Application"
    }
  ]
}
```

**Key Rules**:
- EXACTLY 5 flashcards
- flashcard_id must be 1-5 sequential

**Validation**: 
- Structural: exactly 5 flashcards
- Semantic: character limits, category values

**Storage**: In-memory as `memory_output`, passed to merge step

---

### 7. RecapScene

**Purpose**: Creates 5 video generation prompts for recap section

**Prompt File**: `core/prompts/recap_scene_system_v1.5.txt`

**JSON Output Enforcement**:
```
You must output valid JSON. Do not wrap the JSON in markdown blocks.
```

**Output Schema**:
```json
{
  "section_id": "recap",
  "section_type": "recap",
  "title": "Let's Review",
  "avatar_layout": {
    "position": "right",
    "width_percent": 52
  },
  "video_prompts": [
    {
      "prompt_id": 1,
      "prompt": "100-180 word video generation prompt...",
      "duration_seconds": 8,
      "style": "cinematic"
    }
  ]
}
```

**Key Rules**:
- EXACTLY 5 prompts
- 100-180 words each (API character limit)
- NO banned words (beautiful, stunning, etc)

**Validation**: 
- Structural: exactly 5 prompts
- Semantic: word count, banned phrase check

**Storage**: In-memory as `recap_output`, passed to merge step

---

### 8. ManimCodeGenerator

**Purpose**: Generates executable Python code for Manim animations

**Prompt File**: Inline in `core/agents/manim_code_generator.py`

**Output Format**: RAW PYTHON CODE (not JSON)

**Expected Output**:
```python
title = Text("The Derivative", font_size=48)
title.to_edge(UP)
self.play(Write(title))
# ... more Manim code
```

**Key Rules**:
- Output is Python code for `construct(self)` method body
- Must be syntactically valid Python
- Must use only standard Manim Community objects
- NO imports, NO class definitions

**Validation**:
- Syntax check via `ast.parse()`
- Pattern check for required elements
- Completeness check (not truncated)

**Storage**: Stored in `section.render_spec.manim_scene_spec.manim_code`

---

## Storage Architecture

### Current Flow (V1.5)

```
Pipeline Start
    │
    ▼
┌─────────────────┐
│  SmartChunker   │ → topics[] (in-memory)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SectionPlanner  │ → blueprints[] (in-memory)
└────────┬────────┘
         │
         ▼ (per section)
┌─────────────────┐
│ NarrationWriter │ ─┐
├─────────────────┤  │
│ VisualSpecArtist│  ├→ section_artifacts[] (in-memory)
├─────────────────┤  │
│RendererSpecAgent│ ─┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ MemoryFlashcard │ → memory_output (in-memory)
├─────────────────┤
│   RecapScene    │ → recap_output (in-memory)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Merge Step    │ → presentation{} (in-memory)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   TTS Pass      │ → presentation + audio files
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ManimCodeGenerator│ → presentation + manim_code
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  DISK STORAGE (only here)               │
│  {job_dir}/presentation.json            │
│  {job_dir}/audio/*.mp3                  │
│  {job_dir}/videos/*.mp4                 │
└─────────────────────────────────────────┘
```

### Artifact Persistence (NEW - ISS-149)

With ISS-149 implemented, intermediate artifacts will also be saved:

```
{job_dir}/
├── presentation.json          (final merged output)
├── artifacts/                  (NEW - debug artifacts)
│   ├── 01_chunker.json        (SmartChunker output)
│   ├── 02_planner.json        (SectionPlanner output)
│   ├── 03_section_1_narration.json
│   ├── 04_section_1_visuals.json
│   ├── 05_section_1_render_spec.json
│   ├── ...
│   ├── memory.json
│   ├── recap.json
│   └── manim_failed_sections.json  (for retry)
├── audio/
│   └── section_*.mp3
└── videos/
    └── *.mp4
```

---

## Gap Analysis

### GAP-1: SectionPlanner Avatar Width (ISS-145)

| Aspect | Prompt Says | Code Enforces | Correct Value |
|--------|-------------|---------------|---------------|
| intro | 60% | 52% | 52% |
| summary | 45% | 52% | 52% |
| content | 35% | 52% | 52% |
| example | 35% | 52% | 52% |
| quiz | 35% | 52% | 52% |
| memory | 35% | 52% | 52% |
| recap | 35% | 52% | 52% |

**Fix Location**: `core/prompts/section_planner_system_v1.5.txt` lines 20, 30-38, 47, 53, 59, 65, 71, 77

---

### GAP-2: MemoryFlashcard Avatar Width (ISS-146)

| Aspect | Prompt Says | Code Enforces | Correct Value |
|--------|-------------|---------------|---------------|
| width_percent | 35 | 52 | 52 |

**Fix Location**: `core/prompts/memory_flashcard_system_v1.5.txt` line 14

---

### GAP-3: RecapScene Avatar Width (ISS-147)

| Aspect | Prompt Says | Code Enforces | Correct Value |
|--------|-------------|---------------|---------------|
| width_percent | 35 | 52 | 52 |

**Fix Location**: `core/prompts/recap_scene_system_v1.5.txt` line 12

---

### GAP-4: SmartChunker Deprecated Renderer (ISS-148)

| Aspect | Prompt Says | Should Say |
|--------|-------------|------------|
| suggested_renderer | "remotion\|manim\|video" | "manim\|video\|none" |

**Fix Location**: 
- Rename `core/prompts/smart_chunker_system_v1.4.txt` → `smart_chunker_system_v1.5.txt`
- Update renderer options in prompt
- Update `core/llm_handler.py` to use v1.5 prompt

---

### GAP-5: No Artifact Persistence (ISS-149)

| Aspect | Current | Should Have |
|--------|---------|-------------|
| Agent outputs | In-memory only | Save to `{job_dir}/artifacts/` |
| Debug capability | None | Full artifact trail |
| Retry capability | None | Failed sections logged |

**Fix Location**: `core/pipeline_v15.py` - add artifact save after each agent

---

### GAP-6: RecapScene Word Count Mismatch (ISS-150)

| Aspect | Prompt Says | Code Validates | Correct Value |
|--------|-------------|----------------|---------------|
| Word count | 150-180 | 100+ minimum | 100-180 |

**Fix Location**: `core/prompts/recap_scene_system_v1.5.txt` lines 27, 45

---

### GAP-7: ManimCodeGenerator Validation (ISS-151)

| Aspect | Current | Should Have |
|--------|---------|-------------|
| Output validation | Basic pattern check | Full AST syntax validation |
| Retry logic | Crashes on failure | Graceful retry with max attempts |
| Error handling | Raises exception | Returns empty code + logs error |
| Failed sections | Lost | Saved for later retry |

**Fix Location**: `core/agents/manim_code_generator.py`

---

## Validation Flow

### Agent-Level Validation

Each agent has two validation methods:

1. **`validate_structural(output)`**: JSON schema validation
   - Required fields present
   - Correct data types
   - Array lengths

2. **`validate_semantic(output, input_data)`**: Business logic validation
   - Cross-field consistency
   - Value constraints
   - Reference integrity

### Pipeline-Level Validation

1. **Pre-merge**: Each agent output validated before adding to artifacts
2. **Post-merge**: Final presentation validated against v1.3 schema
3. **Post-TTS**: Audio file existence verified
4. **Post-render**: Video file existence verified

### Error Handling Policy

| Severity | Action |
|----------|--------|
| Structural Error | Retry agent (max 3 attempts) |
| Semantic Warning | Log warning, continue |
| Semantic Error | Retry agent (max 3 attempts) |
| Max Retries Exceeded | Log failure, skip section (no crash) |

---

## Verification Commands

```bash
# Verify all prompts enforce JSON output
grep -l "MUST output.*JSON" core/prompts/*v1.5*.txt

# Verify avatar width in prompts (should be 52)
grep -n "width_percent" core/prompts/*v1.5*.txt

# Verify merge step enforces 52%
grep "width_percent.*52" core/merge_step_v15.py

# Verify player defaults to 52%
grep -n "return 52" player/player.js

# Verify no 'remotion' in V1.5 prompts
grep -c "remotion" core/prompts/*v1.5*.txt
```
