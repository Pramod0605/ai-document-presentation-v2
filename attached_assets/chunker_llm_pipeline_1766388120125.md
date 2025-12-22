# Chunker & LLM Pipeline Documentation

This document details how the content chunking and subsequent LLM calls work in the video generation pipeline, including inputs, outputs, function calls, and JSON responses.

## Overview

The pipeline uses a series of LLM calls to transform raw PDF content into synchronized video slides:

```
PDF → Datalab JSON → Content Extraction → [LLM] Combined Chunker → Slides JSON
                                                      ↓
                                              Audio Generation
                                                      ↓
                                         [LLM] Recap Storyboard
                                                      ↓
                                            HTML Templates
```

## Prompt Loading System

All LLM prompts are externalized in the `prompts/` folder:

```python
# agents/prompt_loader.py

def load_prompt(prompt_name: str, variables: Dict[str, str] = None) -> Dict[str, str]:
    """
    Load prompt from prompts/{prompt_name}.txt
    Returns: {'system_prompt': '...', 'user_prompt': '...'}
    """
    file_path = f"prompts/{prompt_name}.txt"
    
    # Parse sections marked with SYSTEM_PROMPT: and USER_PROMPT:
    # Substitute {variable_name} with provided values
    ...
```

**Available Prompts:**
| File | Purpose |
|------|---------|
| `combined_chunk_narrate.txt` | Main V3 pipeline - chunk + narrate in one call |
| `chunker_smart.txt` | SmartChunker for block grouping |
| `narration_content.txt` | Content slide narration |
| `narration_recap.txt` | Recap Mental Movie narration |
| `recap_storyboard.txt` | Generate 5 visual scenes for recap |
| `exercise_detect.txt` | Detect exercise/MCQ slides |
| `memory_flashcards.txt` | Generate memory flashcards |

---

## Stage 1: Content Extraction (No LLM)

Before any LLM call, content is extracted deterministically from Datalab JSON:

```python
# run_v3_combined.py

def extract_content_and_images(json_data: Dict) -> tuple:
    """
    Extract clean markdown content and image references from Datalab JSON.
    Returns: (topic, blocks_formatted, images_list)
    """
    
    # Walk through JSON tree
    for block in json_data['children']:
        block_type = block.get('block_type')
        
        if block_type == 'SectionHeader':
            # Extract header text
            lines.append(f"## {header_text}")
            
        elif block_type == 'Text':
            # Extract paragraph text
            lines.append(paragraph_text)
            
        elif block_type == 'ListGroup':
            # Extract list items
            for item in block['items']:
                lines.append(f"- {item_text}")
                
        elif block_type == 'Picture':
            # Create placeholder (NOT actual image)
            images.append(f"IMAGE_{count}: {filename}")
    
    return topic, clean_markdown, images_list
```

**Output Example:**
```python
topic = "Reproduction in Organisms"

clean_markdown = """
## 23.1 INTRODUCTION
Living organisms reproduce to maintain continuity of species.

## 23.2 ASEXUAL REPRODUCTION
- Binary fission: Parent divides into two
- Budding: New organism grows from parent
- Spore formation: Spores develop into new organisms
"""

images_list = """
IMAGE_1: binary_fission_diagram.png
IMAGE_2: budding_hydra.jpg
IMAGE_3: spore_formation.png
"""
```

---

## Stage 2: Combined LLM Call (Main Chunker + Narration)

### Function Call

```python
# run_v3_combined.py

def call_combined_llm(topic: str, clean_markdown_content: str, images_list: str) -> Dict:
    """
    Single LLM call that generates slides with synchronized visual + narration.
    Replaces separate SmartChunker + NarrationAgent calls.
    """
    from agents.base_agent import BaseAgent
    from agents.prompt_loader import load_prompt
    
    # 1. Initialize agent with Gemini 2.5 Pro
    agent = BaseAgent(model_name='google/gemini-2.5-pro')
    
    # 2. Load and populate prompt template
    prompts = load_prompt('combined_chunk_narrate', {
        'topic': topic,
        'clean_markdown_content': clean_markdown_content,
        'images_list': images_list
    })
    
    # 3. Call LLM (blocking, waits for response)
    response = agent.call_llm(
        prompts['user_prompt'],
        system_prompt=prompts['system_prompt'],
        max_tokens=16000,
        temperature=0.7
    )
    
    # 4. Parse JSON response
    result = parse_llm_json(response)
    
    return result
```

### LLM Input (Prompt)

**System Prompt:**
```
You are an expert Educational Content Designer and Scriptwriter for Indian students (Grade 8-12).
Your task is to convert raw textbook content into a **Synchronized Video Lesson** in JSON format.

You must structure the lesson so that **visuals appear exactly when the narration speaks about them.**

You must switch personas based on the slide type:
1. **Intro/Summary:** Warm, encouraging teacher ("Namaste students!").
2. **Content:** Clear, academic lecturer who explains concepts step-by-step.
3. **Exercise:** An engaging quizmaster testing knowledge.
4. **Memory:** A helpful teacher summarizing key takeaways.
5. **Recap:** A storyteller creating "Mental Movies" with Indian context and sound effects.
```

**User Prompt:**
```
Create the full synchronized lesson deck for:

TOPIC: Reproduction in Organisms

IMAGES AVAILABLE:
IMAGE_1: binary_fission_diagram.png
IMAGE_2: budding_hydra.jpg
IMAGE_3: spore_formation.png

CONTENT (Clean Markdown):
## 23.1 INTRODUCTION
Living organisms reproduce to maintain continuity of species.
[... rest of content ...]

---
OUTPUT FORMAT (JSON):
{
  "slides": [
    {
      "slide_number": integer,
      "slide_type": "intro" | "summary" | "content" | "exercise" | "memory" | "recap",
      "title": "Slide Title",
      "image_id": "img_filename.jpg" or null,
      
      // FOR CONTENT & EXERCISE SLIDES:
      "segments": [
        {
          "visual": "Text to display on screen",
          "narration_fragment": "Script the avatar speaks",
          "duration_estimate": 5
        }
      ],

      // FOR INTRO, SUMMARY, MEMORY, RECAP SLIDES:
      "visual_content": {...},
      "full_narration": "Complete script for non-segmented slides."
    }
  ]
}
```

### LLM Output (JSON Response)

```json
{
  "slides": [
    {
      "slide_number": 1,
      "slide_type": "intro",
      "title": "Welcome to Reproduction in Organisms",
      "image_id": null,
      "visual_content": {},
      "full_narration": "Namaste students! Welcome to today's lesson on Reproduction in Organisms. Please take out your notebooks and pens. Today we will explore how living beings create copies of themselves. Let's begin!",
      "estimated_duration_seconds": 18
    },
    {
      "slide_number": 2,
      "slide_type": "summary",
      "title": "What You Will Learn",
      "image_id": null,
      "visual_content": {
        "bullet_points": [
          "Understand different types of reproduction",
          "Learn about asexual reproduction methods",
          "Explore sexual reproduction in organisms",
          "Discover how organisms maintain species continuity"
        ]
      },
      "full_narration": "In this module, we will cover four key learning objectives. First, you will understand the fundamental difference between asexual and sexual reproduction...",
      "estimated_duration_seconds": 35
    },
    {
      "slide_number": 3,
      "slide_type": "content",
      "title": "Binary Fission",
      "image_id": "IMAGE_1",
      "segments": [
        {
          "visual": "Binary fission: Parent cell divides into two equal parts",
          "narration_fragment": "Let's begin with Binary Fission. This is a process where the parent cell divides into two equal daughter cells. Think of it like cutting an apple perfectly in half.",
          "duration_estimate": 8
        },
        {
          "visual": "Found in bacteria, amoeba, and paramecium",
          "narration_fragment": "Binary fission is commonly found in single-celled organisms like bacteria, amoeba, and paramecium. These tiny creatures can multiply rapidly using this method.",
          "duration_estimate": 7
        },
        {
          "visual": "Process: DNA replication → Cell elongation → Division",
          "narration_fragment": "The process involves three steps. First, DNA replication creates a copy of genetic material. Then the cell elongates. Finally, the cell membrane pinches inward to form two separate cells.",
          "duration_estimate": 10
        }
      ]
    },
    {
      "slide_number": 15,
      "slide_type": "exercise",
      "title": "Quick Check: Binary Fission",
      "image_id": null,
      "segments": [
        {
          "visual": "Q: Which organism reproduces by binary fission?\nA) Hydra  B) Amoeba  C) Yeast  D) Starfish",
          "narration_fragment": "Let's test your understanding! Which organism reproduces by binary fission? Is it A - Hydra, B - Amoeba, C - Yeast, or D - Starfish?",
          "duration_estimate": 8
        },
        {
          "visual": "Think about it... 🤔",
          "narration_fragment": "Take a moment to think about what we just learned. Remember, we discussed single-celled organisms that divide into two equal parts.",
          "duration_estimate": 5
        },
        {
          "visual": "✓ Answer: B) Amoeba",
          "narration_fragment": "The correct answer is B - Amoeba! Amoeba is a single-celled organism that reproduces by dividing into two identical daughter cells through binary fission.",
          "duration_estimate": 7
        }
      ]
    },
    {
      "slide_number": 29,
      "slide_type": "memory",
      "title": "Remember: R-A-S",
      "image_id": null,
      "visual_content": {
        "flashcards": [
          {
            "letter": "R",
            "title": "REPRODUCTION",
            "description": "Creating copies for species survival"
          },
          {
            "letter": "A",
            "title": "ASEXUAL",
            "description": "Single parent, genetically identical offspring"
          },
          {
            "letter": "S",
            "title": "SEXUAL",
            "description": "Two parents, genetic variation in offspring"
          }
        ]
      },
      "full_narration": "To remember the key concepts, use the simple RAS framework. R stands for Reproduction - the process of creating copies for species survival. A stands for Asexual - reproduction with a single parent producing genetically identical offspring. S stands for Sexual - reproduction involving two parents, creating genetic variation.",
      "estimated_duration_seconds": 45
    },
    {
      "slide_number": 30,
      "slide_type": "recap",
      "title": "Reproduction in Organisms - Recap",
      "image_id": null,
      "visual_content": {
        "infographic_prompt": "Flat vector illustration, bright colors, Indian style. A village scene showing grandmother explaining nature to children, with thought bubbles showing cells dividing, hydra budding, and flowers blooming."
      },
      "full_narration": "Well done, students! Imagine you are sitting with your grandmother in a village garden. She points to a tiny amoeba under a magnifying glass - WHOOSH! It splits in two like magic! Then she shows you a hydra in the pond - POP! A tiny baby grows right from its side like a branch on a tree...",
      "estimated_duration_seconds": 75
    }
  ]
}
```

### JSON Parsing with Repair Logic

```python
# run_v3_combined.py

def parse_llm_json(response: str) -> Dict:
    """Parse JSON from LLM response with repair logic for common errors."""
    response = response.strip()
    
    # 1. Strip markdown code fences
    if '```json' in response:
        start = response.find('```json') + 7
        end = response.rfind('```')
        response = response[start:end].strip()
    
    # 2. Try direct parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # 3. Fix common JSON errors
    json_str = response[response.find('{'):response.rfind('}')+1]
    
    # Remove trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*\]', ']', json_str)
    
    # 4. Repair truncated JSON (if LLM ran out of tokens)
    open_braces = json_str.count('{') - json_str.count('}')
    open_brackets = json_str.count('[') - json_str.count(']')
    
    if open_braces > 0 or open_brackets > 0:
        # Close open strings
        if json_str.count('"') % 2 == 1:
            json_str += '"'
        
        # Remove incomplete trailing entries
        json_str = re.sub(r',\s*\{[^}]*$', '', json_str)
        
        # Close brackets
        json_str += ']' * open_brackets + '}' * open_braces
        
        print(f"  [REPAIRED] Fixed truncated JSON response")
    
    return json.loads(json_str)
```

---

## Stage 3: Audio Generation (No LLM - Edge TTS)

```python
# run_v3_combined.py

def generate_audio_for_slide(slide: Dict, output_dir: str) -> str:
    """Generate audio using Edge TTS (Microsoft's text-to-speech)."""
    
    # Get narration text from slide
    if slide.get('segments'):
        # Combine all segment narrations
        full_text = ' '.join([seg['narration_fragment'] for seg in slide['segments']])
    else:
        full_text = slide.get('full_narration', '')
    
    # Clean text for TTS
    clean_text = clean_narration_for_tts(full_text)
    
    # Generate audio with Edge TTS
    import edge_tts
    voice = "en-IN-NeerjaNeural"  # Indian English female voice
    
    communicate = edge_tts.Communicate(clean_text, voice)
    await communicate.save(output_path)
    
    return output_path
```

---

## Stage 4: Recap Storyboard Generation (Second LLM Call)

For recap slides, a second LLM call generates visual scene descriptions:

### Function Call

```python
# agents/recap_agent.py

class RecapAgent(BaseAgent):
    
    def generate_storyboard(self, narration_text: str) -> List[Dict]:
        """
        Generate exactly 5 visual scenes from recap narration.
        Uses prompts/recap_storyboard.txt
        """
        from agents.prompt_loader import load_prompt
        
        # 1. Load storyboard prompt
        prompts = load_prompt('recap_storyboard', {
            'narration_text': narration_text
        })
        
        # 2. Call LLM
        response = self.call_llm(
            prompts['user_prompt'],
            system_prompt=prompts['system_prompt'],
            max_tokens=2000,
            temperature=0.3
        )
        
        # 3. Parse JSON array
        storyboard = json.loads(response)
        
        return storyboard[:5]  # Exactly 5 scenes
```

### LLM Input (Storyboard Prompt)

```
SYSTEM_PROMPT:
You are a visual storyboard artist for educational videos.
Create exactly 5 scenes that illustrate the Mental Movie narration.

USER_PROMPT:
Break this recap narration into exactly 5 visual scenes:

NARRATION:
Well done, students! Imagine you are sitting with your grandmother in a village garden...

OUTPUT FORMAT (JSON array):
[
  {
    "segment_text": "Text from narration for this scene",
    "image_prompt": "Flat vector illustration, Indian style. [Scene description]",
    "concept_title": "Scene Title",
    "estimated_duration": 12
  }
]
```

### LLM Output (Storyboard JSON)

```json
[
  {
    "segment_text": "Well done, students! Imagine you are sitting with your grandmother in a village garden.",
    "image_prompt": "Flat vector illustration, bright colors, Indian style. A grandmother in traditional saree sitting with grandchildren in a lush village garden, warm golden lighting, purple and blue gradient background.",
    "concept_title": "Welcome Scene",
    "estimated_duration": 10
  },
  {
    "segment_text": "She points to a tiny amoeba under a magnifying glass - WHOOSH! It splits in two like magic!",
    "image_prompt": "Flat vector illustration, bright colors. A magnifying glass revealing an amoeba dividing into two cells, with magical sparkle effects and WHOOSH text, purple and blue gradient background.",
    "concept_title": "Binary Fission Discovery",
    "estimated_duration": 12
  },
  {
    "segment_text": "Then she shows you a hydra in the pond - POP! A tiny baby grows right from its side.",
    "image_prompt": "Flat vector illustration, Indian style. A pond scene with a hydra organism showing budding, baby hydra emerging from parent with POP effect, lily pads and lotus flowers.",
    "concept_title": "Budding Magic",
    "estimated_duration": 12
  },
  {
    "segment_text": "In the kitchen, Amma makes rotis - each new roti comes from the same dough, just like asexual reproduction!",
    "image_prompt": "Flat vector illustration, Indian kitchen scene. Mother in saree making rotis on a tawa, with thought bubbles connecting to cell division diagrams, warm kitchen lighting.",
    "concept_title": "Kitchen Analogy",
    "estimated_duration": 14
  },
  {
    "segment_text": "Remember RAS - Reproduction, Asexual, Sexual. You've mastered it all!",
    "image_prompt": "Flat vector illustration, educational style. Three connected flashcards showing R-A-S mnemonic with icons, glowing brain with memory paths, celebration confetti, purple and blue gradient.",
    "concept_title": "Memory Anchor",
    "estimated_duration": 12
  }
]
```

---

## Stage 5: Image Generation from Storyboard (Third LLM Call)

```python
# agents/visual_engine.py

class VisualEngine(BaseAgent):
    
    def generate_scene_images(self, storyboard: List[Dict], output_dir: str) -> List[Dict]:
        """Generate images for each storyboard scene."""
        
        for i, scene in enumerate(storyboard):
            image_prompt = scene.get('image_prompt', '')
            output_path = f"{output_dir}/scene_{i+1:02d}.png"
            
            # Call image generation (via OpenRouter Gemini)
            result_path = self.generate_image(
                prompt=image_prompt,
                output_path=output_path,
                transparent_bg=False
            )
            
            scene['image_path'] = result_path
        
        return storyboard
```

---

## Complete Pipeline Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STAGE 1: EXTRACTION                                │
│                           (No LLM - Deterministic)                          │
│                                                                              │
│  Input: Datalab JSON file                                                    │
│  Function: extract_content_and_images()                                      │
│                                                                              │
│  Output:                                                                     │
│    - topic: "Reproduction in Organisms"                                      │
│    - clean_markdown: "## 23.1 INTRODUCTION\n..."                            │
│    - images_list: "IMAGE_1: diagram.png\n..."                               │
└────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STAGE 2: COMBINED CHUNKER + NARRATION                    │
│                           (LLM Call #1)                                      │
│                                                                              │
│  Function: call_combined_llm(topic, clean_markdown, images_list)            │
│  Model: google/gemini-2.5-pro                                               │
│  Prompt: prompts/combined_chunk_narrate.txt                                 │
│  Max Tokens: 16,000                                                          │
│  Temperature: 0.7                                                            │
│                                                                              │
│  Input:                                                                      │
│    - {topic}: "Reproduction in Organisms"                                   │
│    - {clean_markdown_content}: Full extracted text                          │
│    - {images_list}: "IMAGE_1: diagram.png\n..."                             │
│                                                                              │
│  Output: JSON with 25-30 slides                                              │
│    {                                                                         │
│      "slides": [                                                             │
│        {"slide_number": 1, "slide_type": "intro", ...},                     │
│        {"slide_number": 2, "slide_type": "summary", ...},                   │
│        {"slide_number": 3, "slide_type": "content", "segments": [...]},     │
│        ...                                                                   │
│        {"slide_number": 30, "slide_type": "recap", ...}                     │
│      ]                                                                       │
│    }                                                                         │
└────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       STAGE 3: AUDIO GENERATION                              │
│                           (No LLM - Edge TTS)                                │
│                                                                              │
│  Function: generate_audio_for_slide(slide, output_dir)                       │
│  Voice: en-IN-NeerjaNeural (Indian English)                                  │
│                                                                              │
│  For each slide:                                                             │
│    - Extract narration text from segments or full_narration                 │
│    - Clean text (remove special chars, fix punctuation)                     │
│    - Generate MP3 via Edge TTS                                               │
│                                                                              │
│  Output:                                                                     │
│    - audio/slide_001_full.mp3                                               │
│    - audio/slide_002_full.mp3                                               │
│    - ...                                                                     │
└────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STAGE 4: RECAP STORYBOARD GENERATION                      │
│                           (LLM Call #2 - Recap Only)                         │
│                                                                              │
│  Function: RecapAgent.generate_storyboard(narration_text)                    │
│  Model: google/gemini-2.5-pro                                               │
│  Prompt: prompts/recap_storyboard.txt                                       │
│  Max Tokens: 2,000                                                           │
│  Temperature: 0.3                                                            │
│                                                                              │
│  Input: Recap slide's full_narration text                                    │
│                                                                              │
│  Output: Array of 5 scene objects                                            │
│    [                                                                         │
│      {"segment_text": "...", "image_prompt": "...", "concept_title": "..."},│
│      ...                                                                     │
│    ]                                                                         │
└────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STAGE 5: RECAP IMAGE GENERATION                           │
│                           (LLM Call #3-7 - Image Gen)                        │
│                                                                              │
│  Function: VisualEngine.generate_scene_images(storyboard, output_dir)        │
│  Model: google/gemini-3-pro-image-preview                                    │
│  Modality: Image generation                                                  │
│                                                                              │
│  For each of 5 scenes:                                                       │
│    - Use scene.image_prompt as generation prompt                            │
│    - Generate PNG image                                                      │
│    - Save to images/recap/scene_01.png, etc.                                │
│                                                                              │
│  Output: 5 scene images in images/recap/ folder                             │
└────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       STAGE 6: HTML RENDERING                                │
│                           (No LLM - Jinja2)                                  │
│                                                                              │
│  For each slide:                                                             │
│    1. Select template based on slide_type                                    │
│    2. Populate with slide data (title, segments, images, audio paths)       │
│    3. Render to html/slide_001.html, etc.                                   │
│                                                                              │
│  Templates:                                                                  │
│    - slide_v3_intro.html                                                    │
│    - slide_v3_summary.html                                                  │
│    - slide_v3_content.html                                                  │
│    - slide_v3_exercise.html                                                 │
│    - slide_v3_memory.html                                                   │
│    - slide_v3_recap.html                                                    │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Alternative: SmartChunker (Legacy Separate Calls)

For the legacy pipeline, chunking is done separately from narration:

### SmartChunker LLM Call

```python
# agents/datalab_parser.py - SmartChunker class

def _single_pass_grouping(self, blocks_formatted, images_list, main_topic, total_blocks):
    """Use chunker_smart.txt prompt for intelligent grouping."""
    
    prompts = load_prompt('chunker_smart', {
        'blocks_formatted': blocks_formatted,
        'images_list': images_list,
        'main_topic': main_topic
    })
    
    response = self.agent.call_llm(
        prompts['user_prompt'],
        system_prompt=prompts['system_prompt'],
        max_tokens=4000,
        temperature=0.2
    )
    
    result = self._parse_chunker_response(response)
    return result['slides']
```

### SmartChunker Output

```json
{
  "slides": [
    {
      "slide_type": "content",
      "title": "Binary Fission",
      "block_ids": [5, 6, 7, 8],
      "image_id": "IMAGE_1"
    },
    {
      "slide_type": "content",
      "title": "Budding in Hydra",
      "block_ids": [9, 10, 11],
      "image_id": "IMAGE_2"
    }
  ]
}
```

### Then NarrationAgent LLM Call

```python
# agents/narration_agent.py

def generate(self, slide_data: Dict) -> Dict:
    """Generate natural narration for a slide."""
    
    prompts = load_prompt('narration_content', {
        'title': slide_data['detected_title'],
        'blocks_formatted': self._format_content_blocks(slide_data['content_blocks'])
    })
    
    response = self.call_llm(
        prompts['user_prompt'],
        system_prompt=prompts['system_prompt'],
        max_tokens=1000,
        temperature=0.7
    )
    
    return {
        'final_narration': response.strip(),
        'word_count': len(response.split())
    }
```

---

## Summary: LLM Calls in V3 Pipeline

| Stage | LLM Model | Prompt File | Purpose | Output |
|-------|-----------|-------------|---------|--------|
| 2 | gemini-2.5-pro | combined_chunk_narrate.txt | Chunk + Narrate | 25-30 slides JSON |
| 4 | gemini-2.5-pro | recap_storyboard.txt | Storyboard scenes | 5 scene objects |
| 5 | gemini-3-pro-image-preview | (image prompt) | Generate images | 5 PNG files |

**Total LLM Calls per Video:** 2 text calls + 5 image calls = 7 API requests

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `run_v3_combined.py` | Main V3 pipeline orchestration |
| `agents/base_agent.py` | OpenRouter API integration |
| `agents/prompt_loader.py` | Load prompts from files |
| `agents/datalab_parser.py` | SmartChunker class |
| `agents/narration_agent.py` | Legacy narration generation |
| `agents/recap_agent.py` | Recap + storyboard generation |
| `agents/visual_engine.py` | Image generation for scenes |
| `prompts/*.txt` | All LLM prompt templates |
