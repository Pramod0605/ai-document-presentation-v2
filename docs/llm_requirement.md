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

| # | Agent | System Prompt | User Prompt | Python File | JSON Enforced | Output Storage |
|---|-------|---------------|-------------|-------------|---------------|----------------|
| 1 | SmartChunker | `smart_chunker_system_v1.5.txt` | `smart_chunker_user_v1.5.txt` | `core/smart_chunker.py` | YES | `artifacts/01_chunker.json` |
| 2 | SectionPlanner | `section_planner_system_v1.5.txt` | `section_planner_user_v1.5.txt` | `core/agents/section_planner.py` | YES | `artifacts/02_planner.json` |
| 3 | NarrationWriter | `narration_writer_system_v1.5.txt` | `narration_writer_user_v1.5.txt` | `core/agents/narration_writer.py` | YES | `artifacts/0X_section_Y_narration.json` |
| 4 | VisualSpecArtist | `visual_spec_artist_system_v1.5.txt` | `visual_spec_artist_user_v1.5.txt` | `core/agents/visual_spec_artist.py` | YES | `artifacts/0X_section_Y_visuals.json` |
| 5 | RendererSpecAgent | `manim_spec_system_v1.5.txt` / `video_prompt_system_v1.5.txt` | `manim_spec_user_v1.5.txt` / `video_prompt_user_v1.5.txt` | `core/agents/renderer_spec_agent.py` | YES | `artifacts/0X_section_Y_render_spec.json` |
| 6 | MemoryFlashcard | `memory_flashcard_system_v1.5.txt` | `memory_flashcard_user_v1.5.txt` | `core/agents/memory_agent.py` | YES | `artifacts/memory.json` |
| 7 | RecapScene | `recap_scene_system_v1.5.txt` | `recap_scene_user_v1.5.txt` | `core/agents/recap_agent.py` | YES | `artifacts/recap.json` |
| 8 | ManimCodeGenerator | `manim_system_prompt.txt` | `manim_user_prompt_template.txt` | `core/agents/manim_code_generator.py` | NO (Python code) | `section.render_spec.manim_scene_spec.manim_code` |

**Note**: All prompts are in `core/prompts/` directory. Artifacts saved to `{job_dir}/artifacts/` per ISS-149.

---

## Detailed Agent Specifications

### 1. SmartChunker

**Purpose**: First pass - extracts logical topics from markdown content

**Prompt Files**:
- System: `core/prompts/smart_chunker_system_v1.5.txt`
- User: `core/prompts/smart_chunker_user_v1.5.txt`

**User Prompt Template Variables**:
- `{markdown_content}` - The full markdown text from PDF conversion
- `{subject}` - Subject area (e.g., "Math", "Science")
- `{grade}` - Grade level (e.g., "Grade 10")

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

**Storage**: `artifacts/01_chunker.json`, passed to SectionPlanner

---

### 2. SectionPlanner

**Purpose**: Plans section structure from topics

**Prompt Files**:
- System: `core/prompts/section_planner_system_v1.5.txt`
- User: `core/prompts/section_planner_user_v1.5.txt`

**User Prompt Template Variables**:
- `{topic_summary}` - SmartChunker output (topics with key_terms, formulas)
- `{subject}` - Subject area
- `{grade}` - Grade level

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

**Storage**: `artifacts/02_planner.json`, passed to per-section agents

---

### 3. NarrationWriter

**Purpose**: Creates TTS narration scripts for one section

**Prompt Files**:
- System: `core/prompts/narration_writer_system_v1.5.txt`
- User: `core/prompts/narration_writer_user_v1.5.txt`

**User Prompt Template Variables**:
- `{section_id}` - Section identifier (e.g., "section_1")
- `{section_type}` - Type (intro, summary, content, example, quiz)
- `{title}` - Section title
- `{learning_goals}` - From SectionPlanner
- `{content}` - Source topic content for this section

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

**Storage**: `artifacts/0X_section_Y_narration.json`, added to `section_artifacts[]`

---

### 4. VisualSpecArtist

**Purpose**: Designs visual elements synchronized with narration segments

**Prompt Files**:
- System: `core/prompts/visual_spec_artist_system_v1.5.txt`
- User: `core/prompts/visual_spec_artist_user_v1.5.txt`

**User Prompt Template Variables**:
- `{section_id}` - Section identifier
- `{section_type}` - Type (content, example)
- `{title}` - Section title
- `{narration_segments}` - NarrationWriter segments (JSON)
- `{renderer}` - Suggested renderer (manim, video, none)

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

**Storage**: `artifacts/0X_section_Y_visuals.json`, added to `section_artifacts[]`

---

### 5. RendererSpecAgent

**Purpose**: Creates renderer-specific specs (Manim or Video prompts)

**Prompt Files**: 
- System (manim): `core/prompts/manim_spec_system_v1.5.txt`
- User (manim): `core/prompts/manim_spec_user_v1.5.txt`
- System (video): `core/prompts/video_prompt_system_v1.5.txt`
- User (video): `core/prompts/video_prompt_user_v1.5.txt`

**User Prompt Template Variables**:
- `{section_id}` - Section identifier
- `{title}` - Section title
- `{visual_beats}` - VisualSpecArtist output (JSON)
- `{narration_segments}` - For timing reference
- `{total_duration}` - Total section duration

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
      "prompt": "100-180 word detailed prompt...",
      "duration_seconds": 5.0,
      "style": "cinematic|documentary|educational|animated"
    }
  ]
}
```

**Validation**: 
- Structural: renderer field, corresponding spec present
- Semantic: object_id references valid, no banned phrases

**Storage**: `artifacts/0X_section_Y_render_spec.json`, added to `section_artifacts[]`

---

### 6. MemoryFlashcard

**Purpose**: Creates exactly 5 flashcards for memory section

**Prompt Files**:
- System: `core/prompts/memory_flashcard_system_v1.5.txt`
- User: `core/prompts/memory_flashcard_user_v1.5.txt`

**User Prompt Template Variables**:
- `{source_content}` - All topics/content from the document
- `{key_terms}` - Extracted key terms
- `{formulas}` - Any formulas mentioned

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

**Storage**: `artifacts/memory.json`, passed to merge step

---

### 7. RecapScene

**Purpose**: Creates 5 video generation prompts for recap section

**Prompt Files**:
- System: `core/prompts/recap_scene_system_v1.5.txt`
- User: `core/prompts/recap_scene_user_v1.5.txt`

**User Prompt Template Variables**:
- `{source_content}` - All topics/content from the document
- `{key_terms}` - Extracted key terms
- `{subject}` - Subject area

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

**Storage**: `artifacts/recap.json`, passed to merge step

---

### 8. ManimCodeGenerator

**Purpose**: Generates executable Python code for Manim animations

**Prompt Files**:
- System: `core/prompts/manim_system_prompt.txt`
- User: `core/prompts/manim_user_prompt_template.txt`

**User Prompt Template Variables**:
- `{section_title}` - Section title
- `{narration_segments}` - Formatted narration segments with timing
- `{visual_description}` - Visual beats description
- `{formulas}` - LaTeX formulas to animate
- `{key_terms}` - Key terms to highlight
- `{total_duration}` - Total animation duration
- `{special_requirements}` - Any special requirements (retry errors, etc.)

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
- Undefined name detection with Manim builtins whitelist
- Pattern check for required elements
- Completeness check (not truncated, no partial code blocks)

**Storage**: `sections[].render_spec.manim_scene_spec.manim_code` (failures: `artifacts/manim_failed_sections.json`)

---

## Storage Architecture

### V1.5 Flow with Artifact Persistence (ISS-149)

```
Pipeline Start
    │
    ▼
┌─────────────────┐
│  SmartChunker   │ → topics[]
│                 │   └── SAVE: artifacts/01_chunker.json
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SectionPlanner  │ → blueprints[]
│                 │   └── SAVE: artifacts/02_planner.json
└────────┬────────┘
         │
         ▼ (per section loop)
┌─────────────────┐
│ NarrationWriter │ → narration_output
│                 │   └── SAVE: artifacts/0X_section_Y_narration.json
├─────────────────┤
│ VisualSpecArtist│ → visuals_output
│                 │   └── SAVE: artifacts/0X_section_Y_visuals.json
├─────────────────┤
│RendererSpecAgent│ → render_spec
│                 │   └── SAVE: artifacts/0X_section_Y_render_spec.json
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ MemoryFlashcard │ → memory_output
│                 │   └── SAVE: artifacts/memory.json
├─────────────────┤
│   RecapScene    │ → recap_output
│                 │   └── SAVE: artifacts/recap.json
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Merge Step    │ → presentation{}
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   TTS Pass      │ → presentation + audio/section_*.mp3
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ManimCodeGenerator│ → presentation.sections[].render_spec.manim_scene_spec.manim_code
│                 │   (failures: SAVE artifacts/manim_failed_sections.json)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  FINAL OUTPUT                           │
│  {job_dir}/presentation.json            │
│  {job_dir}/audio/*.mp3                  │
│  {job_dir}/videos/*.mp4                 │
│  {job_dir}/artifacts/*.json (debug)     │
└─────────────────────────────────────────┘
```

### Directory Structure

```
{job_dir}/
├── presentation.json              (final merged v1.3 schema)
├── artifacts/                     (debug & retry artifacts)
│   ├── 01_chunker.json           (SmartChunker output)
│   ├── 02_planner.json           (SectionPlanner output)
│   ├── 03_section_1_narration.json
│   ├── 04_section_1_visuals.json
│   ├── 05_section_1_render_spec.json
│   ├── 06_section_2_narration.json
│   ├── ...
│   ├── memory.json               (MemoryFlashcard output)
│   ├── recap.json                (RecapScene output)
│   └── manim_failed_sections.json (retry queue)
├── audio/
│   └── section_*.mp3             (TTS output)
└── videos/
    └── *.mp4                     (Manim/WAN renders)
```

---

## LLM Output → presentation.json Field Mapping

This table shows which agent output populates which fields in the final `presentation.json`:

| Agent | Output Field | → presentation.json Location | Section Types |
|-------|--------------|------------------------------|---------------|
| SmartChunker | `source_topic` | `presentation.presentation_info.topic_title` | - |
| SmartChunker | `topics[]` | Used by SectionPlanner (not in final JSON) | - |
| SectionPlanner | `sections[].section_type` | `sections[].section_type` | all |
| SectionPlanner | `sections[].title` | `sections[].title` | all |
| SectionPlanner | `sections[].suggested_renderer` | `sections[].renderer` | all |
| SectionPlanner | `sections[].avatar_width_percent` | `sections[].avatar_layout.width_percent` | all |
| NarrationWriter | `narration.full_text` | (used for TTS, not stored) | intro, summary, content, example, quiz |
| NarrationWriter | `segments[]` | `sections[].segments[]` | intro, summary, content, example, quiz |
| NarrationWriter | `segments[].text` | `sections[].segments[].text` | intro, summary, content, example, quiz |
| NarrationWriter | `segments[].duration` | `sections[].segments[].duration_seconds` (TTS overrides) | all |
| VisualSpecArtist | `visual_beats[]` | `sections[].visual_beats[]` | content, example |
| VisualSpecArtist | `segment_enrichments[]` | Merged into `sections[].segments[].visual_content` | content, example |
| VisualSpecArtist | `display_directives[]` | `sections[].display_directives[]` | content, example |
| RendererSpecAgent | `manim_scene_spec` | `sections[].manim_scene_spec` | content (renderer=manim) |
| RendererSpecAgent | `video_prompts[]` | `sections[].video_prompts[]` | content (renderer=video) |
| MemoryFlashcard | `flashcards[]` | `sections[memory].visual_content` (JSON string) | memory |
| MemoryFlashcard | `title` | `sections[memory].title` | memory |
| RecapScene | `video_prompts[]` | `sections[recap].video_prompts[]` | recap |
| RecapScene | `title` | `sections[recap].title` | recap |
| ManimCodeGenerator | Python code | `sections[].render_spec.manim_scene_spec.manim_code` | content (renderer=manim) |
| TTS Pass | audio duration | `sections[].segments[].duration_seconds` (authoritative) | all |
| TTS Pass | audio file | `sections[].audio_file` | all |

### Section Type → Agent Usage

| Section Type | Agents Used | Notes |
|--------------|-------------|-------|
| intro | SectionPlanner, NarrationWriter | Text-only, avatar explains |
| summary | SectionPlanner, NarrationWriter | Text-only, avatar explains |
| content | SectionPlanner, NarrationWriter, VisualSpecArtist, RendererSpecAgent, ManimCodeGenerator (if manim) | Full pipeline |
| example | SectionPlanner, NarrationWriter, VisualSpecArtist, RendererSpecAgent | Like content but focused on worked examples |
| quiz | SectionPlanner, NarrationWriter | Interactive quiz, no renderer |
| memory | MemoryFlashcard | 5 flashcards, no NarrationWriter |
| recap | RecapScene | 5 video prompts for WAN, no NarrationWriter |

---

## Gap Analysis

### GAP-1: SectionPlanner Avatar Width (ISS-145) - **RESOLVED**

| Aspect | Before | After |
|--------|--------|-------|
| All section types | 60/45/35% | 52% |

**Fix Applied**: Updated all avatar_width_percent values to 52 in `section_planner_system_v1.5.txt`

---

### GAP-2: MemoryFlashcard Avatar Width (ISS-146) - **RESOLVED**

| Aspect | Before | After |
|--------|--------|-------|
| width_percent | 35 | 52 |

**Fix Applied**: Updated width_percent from 35 to 52 in `memory_flashcard_system_v1.5.txt`

---

### GAP-3: RecapScene Avatar Width (ISS-147) - **RESOLVED**

| Aspect | Before | After |
|--------|--------|-------|
| width_percent | 35 | 52 |

**Fix Applied**: Updated width_percent from 35 to 52 in `recap_scene_system_v1.5.txt`

---

### GAP-4: SmartChunker Deprecated Renderer (ISS-148) - **RESOLVED**

| Aspect | Before | After |
|--------|--------|-------|
| Prompt version | v1.4 | v1.5 |
| suggested_renderer | "remotion\|manim\|video" | "manim\|video\|none" |

**Fix Applied**: 
- Created `smart_chunker_system_v1.5.txt` and `smart_chunker_user_v1.5.txt`
- Updated `core/smart_chunker.py` to use v1.5 prompts

---

### GAP-5: No Artifact Persistence (ISS-149) - **RESOLVED**

| Aspect | Before | After |
|--------|--------|-------|
| Agent outputs | In-memory only | Saved to `{job_dir}/artifacts/` |
| Debug capability | None | Full artifact trail |
| Retry capability | None | Failed sections logged to `manim_failed_sections.json` |

**Fix Applied**: 
- Added `_save_artifact()` helper with safe JSON serialization
- Saves: chunker, planner, per-section narration/visuals/render_spec, memory, recap
- Saves `manim_failed_sections.json` for retry capability

---

### GAP-6: RecapScene Word Count Mismatch (ISS-150) - **RESOLVED**

| Aspect | Before | After |
|--------|--------|-------|
| Prompt word count | 150-180 | 100-180 |
| Code validation | 100+ minimum | Matches prompt |

**Fix Applied**: Updated prompt to say 100-180 words in `recap_scene_system_v1.5.txt`

---

### GAP-7: ManimCodeGenerator Validation (ISS-151) - **RESOLVED**

| Aspect | Before | After |
|--------|--------|-------|
| Output validation | Basic pattern check | Full AST syntax validation |
| Undefined names | Not detected | AST-based detection with Manim builtins whitelist |
| Retry logic | Yes (3 attempts) | Yes (3 attempts) - unchanged |
| Error handling | Could crash | Graceful: returns (code, errors) tuple |
| Failed sections | Lost | Saved to `artifacts/manim_failed_sections.json` |

**Fix Applied**: 
- Added `ast` module import and `_check_undefined_names()` method
- Enhanced `_check_syntax()` to use AST parsing
- Pipeline catches all exceptions and logs failed sections for retry

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
