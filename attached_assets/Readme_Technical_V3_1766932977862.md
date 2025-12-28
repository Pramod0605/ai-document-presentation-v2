# V3 Pipeline: Complete Technical Flow

## The Big Picture

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────────┐
│  PDF Upload │───►│ Datalab API  │───►│ LLM Cleaner  │───►│ LLM Chunker │───►│ HTML Generator │
│             │    │ (PDF→JSON)   │    │ (Flash)      │    │ + Narrator  │    │                │
└─────────────┘    └──────────────┘    └──────────────┘    │ (Pro)       │    └────────────────┘
                                                          └──────────────┘            │
                                                                                       ▼
                   ┌────────────────┐    ┌───────────────┐    ┌───────────────┐    ┌────────────────┐
                   │ Presentation   │◄───│ Audio Gen     │◄───│ Timing Calc   │◄───│ Template       │
                   │ Player (HTML)  │    │ (Edge TTS)    │    │ (DirectorAgent)│   │ Rendering      │
                   └────────────────┘    └───────────────┘    └───────────────┘    └────────────────┘
```

---

## STEP 1: PDF Upload → Datalab JSON

### What Happens
User uploads a PDF educational document. The backend sends it to **Datalab API** which converts it to structured JSON.

### Input
```
input/biology_chapter.pdf
```

### Datalab API Output Structure
```json
{
  "children": [
    {
      "block_type": "Page",
      "children": [
        {
          "block_type": "SectionHeader",
          "html": "<h1>Cell Division</h1>"
        },
        {
          "block_type": "Text",
          "html": "<p>The cell cycle consists of interphase and mitotic phase...</p>"
        },
        {
          "block_type": "Picture",
          "id": "img_001",
          "images": {
            "cell_diagram.jpg": "base64_encoded_data..."
          }
        }
      ]
    }
  ]
}
```

---

## STEP 2: Raw Text Extraction

### Code Location
`run_v3_combined.py` → `extract_raw_text_from_json()`

### What Happens
Extracts ALL text from the Datalab JSON without filtering. Creates a flat text dump.

### Input
Datalab JSON with nested blocks

### Output
```
Cell Division
The cell cycle consists of interphase and mitotic phase...
[IMAGE: img_001]
Mitosis is the process of...
Q.1 What is the function of mitochondria?
```

---

## STEP 3: LLM Content Cleaner

### Purpose
Remove PDF artifacts (page numbers, headers, footers) and structure as clean Markdown.

### LLM Details
| Field | Value |
|-------|-------|
| **Model** | `google/gemini-2.5-flash` |
| **Temperature** | 0.3 (low - deterministic) |
| **Max Tokens** | 12,000 |

### Prompt File: `prompts/content_cleaner.txt`

#### SYSTEM_PROMPT:
```
You are an expert Educational Data Cleaner.
Your job is to take raw, messy text extracted from a PDF/JSON and convert it into 
a clean, structured Lecture Outline.

INPUT DATA:
A raw dump of text blocks that may include page numbers, headers, footers, 
and fragmented sentences.

YOUR TASKS:
1. REMOVE NOISE: Delete page numbers (e.g., "23", "Page 5"), copyright notices, 
   and repetitive headers/footers.
2. FIX FRAGMENTS: Merge broken sentences that span across blocks.
3. STRUCTURE: Use Markdown to format the content:
   - Use # for Main Chapters/Topics.
   - Use ## for Sub-topics.
   - Use - for bullet points.
4. IDENTIFY IMAGES: Keep image references [IMAGE_001] in contextual location.
5. PRESERVE EXERCISES: Keep all questions, MCQs exactly as written.

CRITICAL RULES:
- Do NOT summarize or paraphrase. Keep original teaching content verbatim.
- Do NOT delete short valid titles (e.g., "Intro", "Q.1", "Summary").
- ONLY delete non-content artifacts.
```

#### USER_PROMPT:
```
Clean and structure this raw educational content. Remove PDF artifacts but 
preserve ALL teaching material:

{raw_content_from_python}
```

### Input
```
23
Cell Division
© 2024 Publisher Name
The cell cycle consists of...
continued on next page
Q.1 What is mitosis?
```

### Output
```markdown
# Cell Division

The cell cycle consists of interphase and mitotic phase.

## Key Concepts
- Mitosis is the process of cell division
- Meiosis produces gametes

## Questions
Q.1 What is mitosis?
```

---

## STEP 4: Combined Chunker + Narrator (Main LLM Call)

### Purpose
Single LLM call that:
1. Groups content into slides by topic
2. Generates teaching narration for each slide
3. Creates synchronized segment pairs (visual + narration)

### LLM Details
| Field | Value |
|-------|-------|
| **Model** | `google/gemini-2.5-pro` |
| **Temperature** | 0.7 (creative narration) |
| **Max Tokens** | 16,000 |

### Prompt File: `prompts/combined_chunk_narrate.txt`

#### SYSTEM_PROMPT:
```
You are an expert Educational Content Designer and Scriptwriter for Indian 
students (Grade 8-12).

Your task is to convert raw textbook content into a **Synchronized Video Lesson** 
in JSON format.

You must structure the lesson so that **visuals appear exactly when the narration 
speaks about them.**

You must switch personas based on the slide type:
1. **Intro/Summary:** Warm, encouraging teacher ("Namaste students!").
2. **Content:** Clear, academic lecturer who explains step-by-step.
3. **Exercise:** An engaging quizmaster testing knowledge.
4. **Memory:** A helpful teacher summarizing key takeaways.
5. **Recap:** A storyteller creating "Mental Movies" with Indian context.
```

#### USER_PROMPT:
```
Create the full synchronized lesson deck for:

TOPIC: {topic}

IMAGES AVAILABLE:
{images_list}

CONTENT (Clean Markdown):
{clean_markdown_content}
```

### Input
```
TOPIC: Cell Division

IMAGES AVAILABLE:
IMAGE_1: cell_diagram.jpg
IMAGE_2: mitosis_stages.jpg

CONTENT:
# Cell Division
The cell cycle consists of interphase and mitotic phase...
```

### Output (JSON)
```json
{
  "slides": [
    {
      "slide_number": 1,
      "slide_type": "intro",
      "title": "Welcome to Cell Division",
      "visual_content": {},
      "full_narration": "Namaste students! Welcome to today's lesson on Cell Division. Please take out your notebooks. Today we will explore how cells divide and grow. Let's begin!",
      "estimated_duration_seconds": 18
    },
    {
      "slide_number": 3,
      "slide_type": "content",
      "title": "The Cell Cycle",
      "image_id": "cell_diagram.jpg",
      "segments": [
        {
          "visual": "The cell cycle has two main phases",
          "narration_fragment": "Let's start with the basics. The cell cycle has two main phases - the interphase and the mitotic phase.",
          "duration_estimate": 6
        },
        {
          "visual": "Interphase: Cell grows and copies DNA",
          "narration_fragment": "During interphase, the cell grows and copies its DNA. This is the preparation phase before division.",
          "duration_estimate": 7
        },
        {
          "visual": "Mitotic Phase: Cell divides into two",
          "narration_fragment": "In the mitotic phase, the cell actually divides into two identical daughter cells.",
          "duration_estimate": 6
        }
      ]
    },
    {
      "slide_number": 8,
      "slide_type": "exercise",
      "title": "Practice Question",
      "segments": [
        {
          "visual": "Q: What is the main purpose of mitosis?",
          "narration_fragment": "Here's a question for you. What is the main purpose of mitosis? Take a moment to think.",
          "duration_estimate": 5
        },
        {
          "visual": "A) Energy production\nB) Cell division\nC) Digestion\nD) Respiration",
          "narration_fragment": "Is it A - Energy production, B - Cell division, C - Digestion, or D - Respiration? Think carefully!",
          "duration_estimate": 8
        },
        {
          "visual": "Answer: B) Cell division",
          "narration_fragment": "The correct answer is B - Cell division! Mitosis is the process by which a cell divides into two identical daughter cells.",
          "duration_estimate": 7
        }
      ]
    },
    {
      "slide_number": 10,
      "slide_type": "recap",
      "title": "Mental Movie: The Cell Factory",
      "visual_content": {
        "infographic_prompt": "Flat vector illustration, bright colors, Indian style. A busy factory with workers (cells) dividing and multiplying."
      },
      "full_narration": "Imagine a busy factory in Mumbai - DHAM! The machines are running. Each worker is a cell. When the factory needs more workers, a worker doesn't hire new people - instead, WHOOSH! The worker splits into TWO identical workers! That's mitosis - one cell becomes two. Just like how Amma divides rotis equally for everyone at dinner!",
      "estimated_duration_seconds": 45
    }
  ]
}
```

---

## STEP 5: Audio Generation (Edge TTS)

### What Happens
For each slide, concatenate narration fragments and generate audio.

### Code Flow
```python
# For segmented slides (content, exercise)
full_narration = " ".join([seg['narration_fragment'] for seg in slide['segments']])

# For non-segmented slides (intro, summary, memory, recap)
full_narration = slide['full_narration']

# Generate audio
audio_path = generate_audio_edge_tts(full_narration, output_path)
```

### Input
```
"Let's start with the basics. The cell cycle has two main phases - 
the interphase and the mitotic phase. During interphase, the cell 
grows and copies its DNA..."
```

### Output
```
audio/slide_003_full.mp3  (duration: 19.2 seconds)
```

---

## STEP 6: Segment Timing Calculation

### Purpose
Distribute the actual audio duration across segments proportionally.

### Code: `calculate_segment_timings()`

```python
def calculate_segment_timings(slide, audio_duration):
    segments = slide['segments']
    
    # Total estimated duration from LLM
    total_estimate = sum(seg['duration_estimate'] for seg in segments)
    
    # Distribute actual audio time proportionally
    current_time = 0
    for seg in segments:
        proportion = seg['duration_estimate'] / total_estimate
        segment_duration = audio_duration * proportion
        
        seg['start_time'] = current_time
        seg['end_time'] = current_time + segment_duration
        current_time += segment_duration
```

### Input
```json
{
  "segments": [
    {"visual": "Point 1", "duration_estimate": 6},
    {"visual": "Point 2", "duration_estimate": 7},
    {"visual": "Point 3", "duration_estimate": 6}
  ]
}
// audio_duration = 19.2 seconds
```

### Output
```json
{
  "timed_segments": [
    {"visual": "Point 1", "start_time": 0.00, "end_time": 6.06},
    {"visual": "Point 2", "start_time": 6.06, "end_time": 13.13},
    {"visual": "Point 3", "start_time": 13.13, "end_time": 19.20}
  ]
}
```

---

## STEP 7: HTML Template Rendering

### Template Selection
```python
template_map = {
    'intro': 'slide_v3_intro.html',
    'summary': 'slide_v3_summary.html',
    'content': 'slide_v3_content.html',
    'exercise': 'slide_v3_exercise.html',
    'memory': 'slide_v3_memory.html',
    'recap': 'slide_v3_recap.html'
}
```

### Template Context (Data passed to Jinja2)
```python
context = {
    'slide_number': 3,
    'title': 'The Cell Cycle',
    'slide_type': 'content',
    'segments': [
        {'visual': 'Point 1', 'start_time': 0.00, 'end_time': 6.06},
        {'visual': 'Point 2', 'start_time': 6.06, 'end_time': 13.13},
        # ...
    ],
    'duration': 19.2,
    'image_id': 'cell_diagram.jpg',
    'image_base_url': '../images',
    'avatar_video_url': '../assets/avatar.mp4',
    'audio_url': '../audio/slide_003_full.mp3',
    'use_heygen_audio': False
}
```

### HTML Output Structure
```html
<div class="segments-container">
    <div class="segment" 
         data-index="0"
         data-start="0.00" 
         data-end="6.06">
        Point 1
    </div>
    <div class="segment" 
         data-index="1"
         data-start="6.06" 
         data-end="13.13">
        Point 2
    </div>
</div>

<audio id="slideAudio" src="../audio/slide_003_full.mp3"></audio>
```

---

## STEP 8: Narration to Text Sync (The Magic!)

### How It Works

The JavaScript `MediaController` in each slide template listens to audio `timeupdate` events and reveals segments based on the current playback time.

```javascript
handleTimeUpdate() {
    // Get current audio time
    const currentTime = this.audio.currentTime;
    
    // Find which segment should be visible
    let newIndex = -1;
    this.segments.forEach((seg, i) => {
        const start = parseFloat(seg.dataset.start);  // data-start="6.06"
        const end = parseFloat(seg.dataset.end);      // data-end="13.13"
        
        if (currentTime >= start && currentTime < end) {
            newIndex = i;  // This segment is CURRENT
        }
    });
    
    // Update CSS classes for visual effect
    this.segments.forEach((seg, i) => {
        seg.classList.remove('visible', 'current', 'read');
        
        if (i < newIndex) {
            seg.classList.add('read');      // Already spoken - faded
        } else if (i === newIndex) {
            seg.classList.add('current');   // Currently speaking - highlighted
        } else if (i === newIndex + 1) {
            seg.classList.add('visible');   // Coming up next - visible but dim
        }
        // Future segments stay hidden (opacity: 0)
    });
}
```

### Visual States (CSS)
```css
.segment {
    opacity: 0;                    /* Hidden by default */
    transform: translateX(-20px);
}

.segment.visible {
    opacity: 1;
    border-left-color: #8b5cf6;   /* Purple - visible */
}

.segment.current {
    opacity: 1;
    border-left-color: #fbbf24;   /* Yellow - actively speaking */
    background: rgba(251, 191, 36, 0.15);
    box-shadow: 0 4px 20px rgba(251, 191, 36, 0.2);
}

.segment.read {
    opacity: 0.6;                  /* Faded - already spoken */
}
```

### Timeline Visualization
```
Audio:    |----------------------------------------|
          0s        6s         13s        19s

Segment 1: [CURRENT] -> [READ]   -> [READ]   -> [READ]
Segment 2: [HIDDEN]  -> [CURRENT]-> [READ]   -> [READ]
Segment 3: [HIDDEN]  -> [VISIBLE]-> [CURRENT]-> [READ]
```

---

## STEP 9: Presentation Player

### File: `presentation_player.html`

### Architecture
```html
<div class="video-container">
    <!-- Slide loaded as iframe -->
    <iframe id="slideFrame" src="html/slide_001.html"></iframe>
    
    <!-- YouTube-style control bar -->
    <div class="control-bar">
        <button id="playPause">Play</button>
        <div class="timeline">...</div>
        <span class="time-display">0:00 / 5:23</span>
        <button id="fullscreen">Fullscreen</button>
    </div>
</div>
```

### Player to Slide Communication

**Player sends commands to slide:**
```javascript
// Player.js
slideFrame.contentWindow.postMessage('play', '*');
slideFrame.contentWindow.postMessage('pause', '*');
slideFrame.contentWindow.postMessage({ type: 'setVolume', value: 0.5 }, '*');
```

**Slide sends events to player:**
```javascript
// Inside slide template
window.parent.postMessage({ type: 'timeupdate', currentTime: 6.5 }, '*');
window.parent.postMessage({ type: 'audio_ended' }, '*');  // Triggers auto-advance
```

### Auto-Advance Logic
```javascript
// Player.js
window.addEventListener('message', (e) => {
    if (e.data.type === 'audio_ended' && isPlaying) {
        // Move to next slide
        currentSlideIndex++;
        loadSlide(currentSlideIndex);
    }
});
```

---

## STEP 10: Avatar Chroma Key (Green Screen Removal)

### How It Works
The avatar video has a green background. JavaScript removes it in real-time using canvas pixel manipulation.

```javascript
renderFrame() {
    // Draw video frame to canvas
    this.ctx.drawImage(this.video, 0, 0);
    
    // Get pixel data
    const frame = this.ctx.getImageData(0, 0, width, height);
    const data = frame.data;
    
    // Loop through pixels
    for (let i = 0; i < length; i++) {
        const r = data[i * 4 + 0];  // Red
        const g = data[i * 4 + 1];  // Green
        const b = data[i * 4 + 2];  // Blue
        
        // If pixel is "green enough", make it transparent
        if (g > 100 && g > r * 1.4 && g > b * 1.4) {
            data[i * 4 + 3] = 0;  // Set alpha to 0 (transparent)
        }
    }
    
    this.ctx.putImageData(frame, 0, 0);
    requestAnimationFrame(() => this.renderFrame());
}
```

---

## Complete Data Flow Summary

```
PDF File
    |
    v
+-------------------------------------------------------------------------+
| DATALAB API                                                             |
| Input:  PDF binary                                                      |
| Output: Structured JSON with blocks (Text, Picture, SectionHeader)      |
+-------------------------------------------------------------------------+
    |
    v
+-------------------------------------------------------------------------+
| EXTRACT RAW TEXT (Python)                                               |
| Input:  Datalab JSON                                                    |
| Output: Flat text with [IMAGE] markers                                  |
+-------------------------------------------------------------------------+
    |
    v
+-------------------------------------------------------------------------+
| LLM: CONTENT CLEANER (gemini-2.5-flash)                                 |
| Input:  Raw text dump                                                   |
| Output: Clean Markdown (headers, bullets, preserved exercises)          |
+-------------------------------------------------------------------------+
    |
    v
+-------------------------------------------------------------------------+
| LLM: COMBINED CHUNKER + NARRATOR (gemini-2.5-pro)                       |
| Input:  Clean Markdown + Image list + Topic                             |
| Output: JSON with slides containing:                                    |
|         - slide_type (intro/content/exercise/memory/recap)              |
|         - segments[] with visual + narration_fragment + duration_estimate|
|         - full_narration (for non-segmented slides)                     |
+-------------------------------------------------------------------------+
    |
    v
+-------------------------------------------------------------------------+
| AUDIO GENERATION (Edge TTS)                                             |
| Input:  Narration text per slide                                        |
| Output: MP3 audio files + actual duration in seconds                    |
+-------------------------------------------------------------------------+
    |
    v
+-------------------------------------------------------------------------+
| SEGMENT TIMING (Python calculation)                                     |
| Input:  Segments with duration_estimate + actual audio duration         |
| Output: Segments with start_time, end_time (proportional distribution)  |
+-------------------------------------------------------------------------+
    |
    v
+-------------------------------------------------------------------------+
| HTML TEMPLATE RENDERING (Jinja2)                                        |
| Input:  Slide data with timed segments                                  |
| Output: HTML files with data-start, data-end attributes on segments     |
+-------------------------------------------------------------------------+
    |
    v
+-------------------------------------------------------------------------+
| PRESENTATION PLAYER (JavaScript)                                        |
| - Loads slides in iframe                                                |
| - Controls playback via postMessage                                     |
| - Receives timeupdate events for timeline sync                          |
| - Auto-advances on audio_ended                                          |
+-------------------------------------------------------------------------+
    |
    v
+-------------------------------------------------------------------------+
| SLIDE RENDERING (JavaScript in each slide)                              |
| - Audio timeupdate -> compare currentTime with data-start/data-end      |
| - Add CSS classes: current (yellow), read (faded), visible (upcoming)   |
| - Avatar chroma key removes green pixels in real-time                   |
+-------------------------------------------------------------------------+
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `run_v3_combined.py` | Main pipeline orchestrator |
| `prompts/content_cleaner.txt` | LLM prompt for cleaning raw text |
| `prompts/combined_chunk_narrate.txt` | LLM prompt for slide generation |
| `agents/base_agent.py` | OpenRouter API integration |
| `agents/prompt_loader.py` | Load prompts from files |
| `templates/slide_v3_content.html` | Content slide template with sync logic |
| `templates/slide_v3_exercise.html` | Exercise/quiz slide template |
| `templates/slide_v3_recap.html` | Recap storytelling template |

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | LLM access via OpenRouter |
| `DATALAB_API_KEY` | PDF to JSON conversion |
| `EDGE_TTS_VOICE` | TTS voice (default: `en-IN-PrabhatNeural`) |
| `V3_OUTPUT_DIR` | Override output directory |

---

## Output Structure

```
output/v3/{job_id}/
├── audio/                    # Edge TTS audio files
│   ├── slide_001_full.mp3
│   ├── slide_002_full.mp3
│   └── ...
├── html/                     # Rendered HTML slides
│   ├── slide_001.html
│   ├── slide_002.html
│   └── ...
├── images/                   # Extracted + generated images
│   ├── recap/                # Recap storyboard images
│   │   ├── recap_scene_01.png
│   │   └── ...
│   └── *.jpg                 # PDF images
├── assets/                   # Avatar videos
│   └── avatar.mp4
├── slides_processed.json     # Full slide data with timing
└── presentation_player.html  # Main entry point
```

---

## Running the Pipeline

```bash
# Run full pipeline with PDF input
python run_v3_job.py --input input/your_document.pdf

# With custom job name
python run_v3_job.py --input input/your_document.pdf --name "biology-chapter-1"

# View output
# Open output/v3/{job_id}/presentation_player.html in browser
```
