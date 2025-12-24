# Display Requirements Specification

**Version**: 1.0  
**Last Updated**: 2025-12-24  
**Status**: Reference Document  

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Summary](#architecture-summary)
3. [File References](#file-references)
4. [Stage Layout](#stage-layout)
5. [Section Types & Display Behavior](#section-types--display-behavior)
6. [Avatar Behavior & Sizing](#avatar-behavior--sizing)
7. [Display Directives System](#display-directives-system)
8. [Timing & Synchronization](#timing--synchronization)
9. [Current vs Required Behavior](#current-vs-required-behavior)
10. [Gap Analysis](#gap-analysis)

---

## Overview

This document defines how the AI Animated Education player displays educational content. It serves as the single source of truth for understanding:

- **WHAT** is displayed (text, video, avatar, bullets)
- **WHERE** components are positioned (left, right, center, fullscreen)
- **WHEN** transitions occur (timing from narration segments)
- **HOW** the display_directives control layer visibility

### Core Principle

> **"The Player is DUMB"** - The player executes JSON instructions without making any decisions about layout, timing, or pedagogy. All intelligence comes from the LLM pipeline.

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PIPELINE FLOW                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PDF/MD Input                                                            │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────┐    ┌───────────────┐    ┌──────────────────┐               │
│  │ Chunker │───▶│ SectionPlanner│───▶│ NarrationWriter  │               │
│  └─────────┘    └───────────────┘    └────────┬─────────┘               │
│                                               │                          │
│       ┌───────────────────────────────────────┘                          │
│       ▼                                                                  │
│  ┌─────────────────┐    ┌────────────────┐    ┌─────────────┐           │
│  │ VisualSpecArtist│───▶│RendererSpec   │───▶│ Memory/Recap │           │
│  └─────────────────┘    └────────────────┘    └──────┬──────┘           │
│                                                       │                  │
│       ┌───────────────────────────────────────────────┘                  │
│       ▼                                                                  │
│  ┌─────────────┐    ┌─────────┐    ┌──────────────────────────┐         │
│  │ Merge Step  │───▶│   TTS   │───▶│ presentation.json OUTPUT │         │
│  └─────────────┘    └─────────┘    └─────────────┬────────────┘         │
│                                                   │                      │
│                                                   ▼                      │
│                                          ┌──────────────┐                │
│                                          │  player.js   │                │
│                                          │  index.html  │                │
│                                          └──────────────┘                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File References

| Component | File Location | Purpose |
|-----------|--------------|---------|
| **Player Logic** | `player/player.js` | JavaScript that reads presentation.json and controls all display |
| **Player UI** | `player/index.html` | HTML structure and CSS for stage, layers, controls |
| **Presentation Data** | `player/jobs/{job_id}/presentation.json` | Single source of truth for playback |
| **Videos** | `player/jobs/{job_id}/videos/topic_*.mp4` | Manim/WAN rendered videos |
| **Audio** | `player/jobs/{job_id}/section_*.mp3` | TTS audio files |
| **V1.5 Spec** | `docs/v1.5_requirements.json` | Pipeline architecture reference |

---

## Stage Layout

### Stage Dimensions

```
┌─────────────────────────────────────────────────────────────────┐
│                        STAGE (1280 x 720)                       │
│                                                                 │
│  ┌──────────────────────────────┐  ┌──────────────────────────┐│
│  │                              │  │                          ││
│  │       CONTENT-BOX            │  │       VIDEO-BOX          ││
│  │       (55% width)            │  │       (40% width)        ││
│  │                              │  │                          ││
│  │  - Title (h1)                │  │  - inline-video          ││
│  │  - segments-list (bullets)   │  │  - Manim/WAN content     ││
│  │  - Formulas                  │  │                          ││
│  │                              │  │                          ││
│  └──────────────────────────────┘  └──────────────────────────┘│
│                                                                 │
│                                         ┌───────────────────┐   │
│                                         │   AVATAR-CANVAS   │   │
│                                         │   (30% default)   │   │
│                                         │   Bottom-right    │   │
│                                         └───────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Z-Index Stack

| Z-Index | Element | Purpose |
|---------|---------|---------|
| 0 | `#bg-image-layer` | Background images |
| 1 | `#scene-video` | Full-screen video (khan mode) |
| 5 | `#content-wrapper` | Contains content-box and video-box |
| 20 | `#avatar-canvas` | Avatar display |
| 25 | `#content-wrapper` (content-video mode) | Raised for video swap |

### Layout Modes (CSS Classes on #stage)

| Mode | Class | Description |
|------|-------|-------------|
| Side | `mode-side` | Avatar right (85% height), content left |
| Center | `mode-center` | Avatar center-right, content left (65% max) |
| Content Video | `mode-content-video` | Content left + video right, avatar reduced |
| Khan | `mode-khan` | Full-screen video, no content box |
| Image | `mode-image` | Background image visible, content hidden |

---

## Section Types & Display Behavior

### Section 1: INTRO

```
┌─────────────────────────────────────────────────────────────────┐
│                           INTRO LAYOUT                          │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │              WELCOME TEXT / BULLET POINTS                │   │
│  │                                                          │   │
│  │    "Welcome to Definite Integrals!"                      │   │
│  │    - Explore Definite Integrals                          │   │
│  │    - Understand Areas Under Curves                       │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│                        ┌───────────────────┐                    │
│                        │                   │                    │
│                        │      AVATAR       │                    │
│                        │     (CENTER)      │                    │
│                        │   50% width       │                    │
│                        │   Welcoming       │                    │
│                        │                   │                    │
│                        └───────────────────┘                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

| Attribute | Current Value | Required Value |
|-----------|---------------|----------------|
| **Avatar Position** | center | center |
| **Avatar Size** | 50% width | 50% width |
| **Avatar Visibility** | required | required |
| **Content** | Text/bullets (LLM generated) | Text/bullets (LLM generated) |
| **Video** | None | None |
| **Renderer** | none | none |
| **display_directives** | text=show, visual=hide, avatar=show | text=show, visual=hide, avatar=show |

**Narration Style**: Welcoming, "Hello and welcome to our exploration of..."

---

### Section 2: SUMMARY

```
┌─────────────────────────────────────────────────────────────────┐
│                          SUMMARY LAYOUT                         │
│                                                                 │
│  ┌─────────────────────────────┐   ┌──────────────────────────┐ │
│  │                             │   │                          │ │
│  │    WHAT YOU'LL LEARN        │   │        AVATAR            │ │
│  │                             │   │        (RIGHT)           │ │
│  │  - Define definite integral │   │        30% width         │ │
│  │  - Properties overview      │   │        Medium size       │ │
│  │  - Fundamental theorem      │   │        Explaining        │ │
│  │  - Worked examples          │   │                          │ │
│  │                             │   │                          │ │
│  └─────────────────────────────┘   └──────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

| Attribute | Current Value | Required Value |
|-----------|---------------|----------------|
| **Avatar Position** | left (incorrect) | right |
| **Avatar Size** | 30% width | 30% width (medium) |
| **Avatar Visibility** | required | required |
| **Content** | Bullet points (LLM generated) | Bullet points (LLM generated) |
| **Video** | None | None |
| **Renderer** | none | none |
| **display_directives** | text=show, visual=hide, avatar=show | text=show, visual=hide, avatar=show |

**Narration Style**: Overview, "In this lesson, you will learn..."

---

### Section 3-6: CONTENT

```
┌─────────────────────────────────────────────────────────────────┐
│                       CONTENT LAYOUT (TEXT)                     │
│                                                                 │
│  ┌─────────────────────────────┐   ┌──────────────────────────┐ │
│  │                             │   │                          │ │
│  │   CONTENT FROM SOURCE       │   │        AVATAR            │ │
│  │   (P7: Input file only!)    │   │        (RIGHT)           │ │
│  │                             │   │        30% width         │ │
│  │  - Key concept 1            │   │        Medium size       │ │
│  │  - Key concept 2            │   │        Explaining        │ │
│  │  - Formula: ∫f(x)dx         │   │                          │ │
│  │                             │   │                          │ │
│  └─────────────────────────────┘   └──────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

                              ▼ SWAP TO VIDEO ▼

┌─────────────────────────────────────────────────────────────────┐
│                      CONTENT LAYOUT (VIDEO)                     │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                                                           │  │
│  │                    MANIM VIDEO                            │  │
│  │                    (FULLSCREEN)                           │  │
│  │                                                           │  │
│  │     [Animated graph, equations, visual explanation]       │  │
│  │                                                           │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                            ┌──────────────────┐ │
│                                            │ AVATAR (small)   │ │
│                                            │ gesture_only     │ │
│                                            └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

| Attribute | Current Value | Required Value |
|-----------|---------------|----------------|
| **Avatar Position** | right | right |
| **Avatar Size** | 30% width | 30% (medium), reduce when video |
| **Avatar Visibility** | optional/hidden (varies) | optional - show during text, gesture_only during video |
| **Content** | Bullets from source (P7) | Bullets from source (P7 ONLY) |
| **Video** | Manim animation | Manim animation (fullscreen when playing) |
| **Renderer** | manim | manim |
| **display_directives** | Varies per segment | text=show/hide, visual=show/hide (mutual exclusion) |

**Narration Style**: Teaching, explains concept then shows visual

**Critical Rule (P7)**: Content MUST come from input PDF/MD file only. NO fabricated content.

---

### Section 7: EXAMPLE

```
┌─────────────────────────────────────────────────────────────────┐
│                         EXAMPLE LAYOUT                          │
│                                                                 │
│  ┌─ WORKED EXAMPLE ─────────────────┐  ┌──────────────────────┐ │
│  │                                  │  │                      │ │
│  │  Problem:                        │  │       AVATAR         │ │
│  │  Evaluate ∫₀² (3x² + 2x) dx      │  │       (RIGHT)        │ │
│  │                                  │  │       30% width      │ │
│  │  Step 1: Find antiderivative     │  │       Medium size    │ │
│  │  Step 2: Apply bounds            │  │       Explaining     │ │
│  │  Step 3: Calculate result        │  │                      │ │
│  │                                  │  │                      │ │
│  │  Answer: 16                      │  │                      │ │
│  └──────────────────────────────────┘  └──────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

| Attribute | Current Value | Required Value |
|-----------|---------------|----------------|
| **Avatar Position** | hidden | right |
| **Avatar Size** | 30% | 30% (medium) |
| **Avatar Visibility** | hidden | optional |
| **Content** | Step-by-step solution | Step-by-step from source |
| **Video** | Manim (optional) | Manim showing solution steps |
| **Renderer** | manim | manim |
| **display_directives** | text=show | text=show, visual=show (for worked steps) |

**Trigger**: Only appears if source content contains worked examples (Director flags it)

**Narration Style**: "Let's work through an example together..."

---

### Section 8: MEMORY (Flashcards)

```
┌─────────────────────────────────────────────────────────────────┐
│                         MEMORY LAYOUT                           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │  │
│  │  │ FLASHCARD 1 │  │ FLASHCARD 2 │  │ FLASHCARD 3 │        │  │
│  │  │             │  │             │  │             │        │  │
│  │  │ Q: What is  │  │ Q: Formula? │  │ Q: When to  │        │  │
│  │  │ a definite  │  │             │  │ use FTC?    │        │  │
│  │  │ integral?   │  │ A: ∫ₐᵇf(x) │  │             │        │  │
│  │  │             │  │             │  │ A: When...  │        │  │
│  │  │ A: Area     │  │             │  │             │        │  │
│  │  │ under curve │  │             │  │             │        │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │  │
│  │                                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐                         │  │
│  │  │ FLASHCARD 4 │  │ FLASHCARD 5 │                         │  │
│  │  │             │  │             │                         │  │
│  │  └─────────────┘  └─────────────┘                         │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                            ┌──────────────────┐ │
│                                            │ AVATAR (hidden)  │ │
│                                            └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

| Attribute | Current Value | Required Value |
|-----------|---------------|----------------|
| **Avatar Position** | hidden | right (medium) |
| **Avatar Size** | 0% | 30% (medium) |
| **Avatar Visibility** | hidden | optional/show |
| **Content** | 5 Flashcards (LLM generated) | 3-5 Flashcards (LLM generated from source) |
| **Video** | None | None |
| **Renderer** | none | none |
| **display_directives** | text=hide, visual=show | text=hide, visual=show, avatar=show |

**Trigger**: Always generated (mandatory section)

**Narration Style**: "Let's remember the key points..." (brief)

---

### Section 9: RECAP

```
┌─────────────────────────────────────────────────────────────────┐
│                          RECAP LAYOUT                           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                                                           │  │
│  │                     WAN VIDEO                             │  │
│  │                   (FULLSCREEN)                            │  │
│  │                                                           │  │
│  │   [AI-generated video summarizing key concepts]           │  │
│  │                                                           │  │
│  │   Scene 1: Introduction recap                             │  │
│  │   Scene 2: Core concept animation                         │  │
│  │   Scene 3: Formula visualization                          │  │
│  │   Scene 4: Application example                            │  │
│  │   Scene 5: Closing summary                                │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                            ┌──────────────────┐ │
│                                            │ AVATAR (hidden)  │ │
│                                            │ or small/gesture │ │
│                                            └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

| Attribute | Current Value | Required Value |
|-----------|---------------|----------------|
| **Avatar Position** | hidden | right (small) or hidden |
| **Avatar Size** | 0% | 0-20% (small if shown) |
| **Avatar Visibility** | hidden | hidden or gesture_only |
| **Content** | None (video only) | None (video only) |
| **Video** | WAN/Kie.ai generated | WAN/Kie.ai generated (5 scenes) |
| **Renderer** | wan_video | wan_video |
| **display_directives** | text=hide, visual=show | text=hide, visual=show, avatar=hide |

**Trigger**: Always generated (mandatory section)

**Narration Style**: Video has its own audio/narration

---

## Avatar Behavior & Sizing

### Avatar Positioning (from presentation.json)

```json
{
  "avatar_global": {
    "style": "teacher",
    "default_position": "right",
    "default_width_percent": 30,
    "gesture_enabled": true
  }
}
```

### Section-Level Avatar Layout

```json
{
  "avatar_layout": {
    "visibility": "required|optional|hidden",
    "mode": "floating|compact",
    "position": "center|left|right|hidden",
    "width_percent": 0-100
  }
}
```

### Avatar Size Reference

| Size | width_percent | Height | Use Case |
|------|---------------|--------|----------|
| Large | 50% | 85% | Intro (center stage) |
| Medium | 30% | 85% | Content, Summary, Example |
| Small | 20% | 60% | During video playback |
| Hidden | 0% | 0% | Recap video, Memory flashcards |

### Avatar Visibility States

| State | Behavior |
|-------|----------|
| `required` | Always visible, prominent |
| `optional` | Can be hidden during video |
| `hidden` | Not displayed |
| `gesture_only` | Small, gesturing but not speaking |

---

## Display Directives System

### Layer Control (from LayerController in player.js)

```javascript
class LayerController {
  applyDirectives(segment, sectionType, segmentIndex) {
    const textLayer = directives.text_layer;     // 'show' | 'hide' | 'swap'
    const visualLayer = directives.visual_layer; // 'show' | 'hide' | 'replace'
    const avatarLayer = directives.avatar_layer; // 'show' | 'hide' | 'gesture_only'
  }
}
```

### Mutual Exclusion Rule (Critical)

> **text_layer='show' + visual_layer='show' is FORBIDDEN**

Only ONE primary attention layer at a time:
- Either text is prominent (text=show, visual=hide)
- Or visuals are prominent (text=hide, visual=show)

### Display Directive Flow

```
Segment 1: text=show, visual=hide   → Text visible, video hidden
Segment 2: text=show, visual=hide   → Text visible, video hidden
Segment 3: text=hide, visual=show   → Text fades, video appears
Segment 4: text=hide, visual=show   → Video continues
Segment 5: text=show, visual=hide   → Video hides, text returns
```

### Segment-Level vs Section-Level

```json
{
  "sections": [{
    "display_directives": [           // Section-level array (one per segment)
      {"text_layer": "show", "visual_layer": "hide", "avatar_layer": "show"},
      {"text_layer": "hide", "visual_layer": "show", "avatar_layer": "gesture_only"}
    ],
    "narration": {
      "segments": [{
        "display_directives": {       // Segment-level (embedded)
          "text_layer": "show",
          "visual_layer": "hide",
          "avatar_layer": "show"
        }
      }]
    }
  }]
}
```

---

## Timing & Synchronization

### Duration Source

| Component | Source | File |
|-----------|--------|------|
| Segment duration | TTS actual audio length | `section_*.mp3` measured via mutagen |
| Section duration | Sum of segment durations | Calculated in merge step |
| Video duration | Manim/WAN render output | `topic_*.mp4` |

### Sync Invariants

```
sum(segment.duration_seconds) = section.narration.total_duration_seconds
visual_beat[i].sync_to_segment = segment_id
display_directives[i] corresponds to segment[i]
```

### Audio Files

| Pattern | Content |
|---------|---------|
| `section_{N}.mp3` | Consolidated section audio |
| `{section}_{segment}.mp3` | Individual segment audio (backup) |

---

## Current vs Required Behavior

### Summary Comparison

| Section | Current Avatar | Required Avatar | Gap |
|---------|----------------|-----------------|-----|
| Intro | center, 50% | center, 50% | OK |
| Summary | left, 30% | right, 30% | POSITION WRONG |
| Content | varies | right, 30% (medium) | INCONSISTENT |
| Example | hidden | right, 30% | AVATAR MISSING |
| Memory | hidden | right, 30% | AVATAR MISSING |
| Recap | hidden | hidden or small | OK |

### Display Directive Issues

| Issue | Description | Status |
|-------|-------------|--------|
| Content video swap | text=hide before video ready | FIXED (ISS-062) |
| Mutual exclusion | text+visual both show | ENFORCED |
| Avatar during video | Should be gesture_only | PARTIAL |

---

## Gap Analysis

### Critical Gaps (Must Fix)

| ID | Gap | Impact | Solution |
|----|-----|--------|----------|
| GAP-001 | Summary avatar position is "left" | Inconsistent with requirement | Update SectionPlanner prompt to always use "right" for summary |
| GAP-002 | Example section avatar is hidden | Missing teacher presence | Update SectionPlanner to set visibility="optional", position="right" |
| GAP-003 | Memory section avatar is hidden | Inconsistent with requirement | Update MemoryAgent output to include avatar_layout |
| GAP-004 | Content sections have inconsistent avatar | Some hidden, some optional | Standardize to visibility="optional", position="right" |

### Minor Gaps (Nice to Have)

| ID | Gap | Impact | Solution |
|----|-----|--------|----------|
| GAP-005 | Recap avatar could be small | User preference | Add avatar_layout with small size to RecapAgent |
| GAP-006 | Memory flashcards fill screen | Avatar could accompany | CSS update for memory layout |

### LLM Prompt Updates Needed

| Agent | Current Behavior | Required Update |
|-------|------------------|-----------------|
| SectionPlanner | Inconsistent avatar_layout | Standardize: intro=center, all others=right |
| VisualSpecArtist | Avatar hidden during video | Use gesture_only instead of hidden |
| MemoryFlashcard | No avatar_layout | Add avatar_layout with right, 30% |
| RecapScene | No avatar_layout | Add avatar_layout with hidden or small |

---

## Appendix: Key Files Quick Reference

### player/index.html Structure

```html
<div id="stage" class="mode-side">
  <video id="scene-video"></video>           <!-- Full-screen video -->
  <img id="bg-image-layer">                  <!-- Background image -->
  <div id="scene-label"></div>               <!-- Scene title -->
  <div id="image-display-layer"></div>       <!-- Image overlay -->
  
  <div id="content-wrapper">
    <div id="content-box">
      <h1 id="slide-title"></h1>             <!-- Section title -->
      <div id="segments-list"></div>         <!-- Bullet points -->
    </div>
    <div id="video-box">
      <video id="inline-video"></video>      <!-- Manim video -->
    </div>
  </div>
  
  <canvas id="avatar-canvas"></canvas>       <!-- Avatar display -->
  <audio id="main-audio"></audio>            <!-- TTS audio -->
</div>
```

### player/player.js Key Classes

| Class | Purpose |
|-------|---------|
| `SlideValidator` | Validates v1.3 presentation.json fields |
| `LayerController` | Applies display_directives to show/hide layers |
| `VideoBufferManager` | Preloads and manages video playback |

### presentation.json Schema (v1.5)

```json
{
  "spec_version": "v1.5",
  "title": "string",
  "subject": "string",
  "grade": "string",
  "avatar_global": {
    "style": "teacher",
    "default_position": "right",
    "default_width_percent": 30,
    "gesture_enabled": true
  },
  "sections": [{
    "section_type": "intro|summary|content|example|memory|recap",
    "title": "string",
    "renderer": "none|manim|wan_video",
    "avatar_layout": {
      "visibility": "required|optional|hidden",
      "mode": "floating|compact",
      "position": "center|left|right|hidden",
      "width_percent": 0-100
    },
    "narration": {
      "full_text": "string",
      "segments": [{
        "segment_id": 1,
        "text": "string",
        "duration_seconds": 12.5,
        "gesture_hint": "welcoming|explaining|emphasizing",
        "visual_content": {
          "bullet_points": [{"level": 1, "text": "string"}],
          "formula": "string|null"
        },
        "display_directives": {
          "text_layer": "show|hide|swap",
          "visual_layer": "show|hide|replace",
          "avatar_layer": "show|hide|gesture_only"
        },
        "audio_file": "1_1.mp3"
      }],
      "total_duration_seconds": 34.78
    },
    "display_directives": [/* array matching segments */],
    "video_path": "videos/topic_3.mp4",
    "audio_path": "section_3.mp3"
  }]
}
```

---

*End of Document*
