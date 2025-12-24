# Manim Code Generation - Implementation Guide

## 🎯 Quick Start

Follow these steps to integrate Manim video generation into your pipeline.

---

## Step 1: Use the Correct Prompts

### System Prompt
**Location**: `manim-renderer/prompts/manim_system_prompt.txt`

**When to use**: Set this as the system message for ALL LLM calls that generate Manim code.

**LLM to use**: **Claude Sonnet 4.5** via OpenRouter
- Model ID: `anthropic/claude-sonnet-4.5`
- OpenRouter API: `https://openrouter.ai/api/v1`

```python
import openai

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="YOUR_OPENROUTER_API_KEY"
)

# Read system prompt
with open("manim-renderer/prompts/manim_system_prompt.txt", "r") as f:
    system_prompt = f.read()
```

### User Prompt Template
**Location**: `manim-renderer/prompts/manim_user_prompt_template.txt`

**How to use**: Fill in the template variables with your data.

---

## Step 2: Prepare Timing Information

### ✅ RECOMMENDED: Segment-Level Timing

**Before generating Manim code**, you need:

1. **Narration text** (what will be spoken)
2. **Narration segments** with timing
3. **Visual description** for each segment

### Example Data Structure

```python
section_data = {
    "section_id": "3",
    "section_title": "Definite Integral",
    
    # Narration segments with timing
    "narration_segments": [
        {
            "start": 0,
            "duration": 5.2,
            "text": "The definite integral represents the signed area under a curve.",
            "visual": "Show title, create axes, and labels"
        },
        {
            "start": 5.2,
            "duration": 8.5,
            "text": "For a parabola y equals x squared, we can visualize this area as a colored region.",
            "visual": "Plot curve, fill area with semi-transparent blue"
        },
        {
            "start": 13.7,
            "duration": 6.3,
            "text": "We use the integral symbol to denote this calculation.",
            "visual": "Display integral notation with labeled components"
        }
    ],
    
    # Total duration
    "total_duration": 20.0,  # sum of all segment durations
    
    # Mathematical content
    "formulas": ["∫ₐᵇ f(x)dx", "A = ∫₋₁² x² dx"],
    "key_terms": ["integral symbol", "upper limit", "lower limit", "integrand"]
}
```

---

## Step 3: Generate Manim Code with LLM

### Complete Code Example

```python
import openai
import json

def generate_manim_code(section_data, openrouter_api_key):
    """
    Generate Manim code synchronized to narration timing.
    
    Args:
        section_data: Dictionary with narration segments and timing
        openrouter_api_key: Your OpenRouter API key
        
    Returns:
        Python code string ready to use in JSON
    """
    
    # 1. Read system prompt
    with open("manim-renderer/prompts/manim_system_prompt.txt", "r") as f:
        system_prompt = f.read()
    
    # 2. Format narration segments for prompt
    segments_text = ""
    for i, seg in enumerate(section_data["narration_segments"], 1):
        segments_text += f"""
Segment {i} ({seg['start']}-{seg['start'] + seg['duration']}s):
- Narration: "{seg['text']}"
- Visual: {seg['visual']}
"""
    
    # 3. Read and fill user prompt template
    with open("manim-renderer/prompts/manim_user_prompt_template.txt", "r") as f:
        user_template = f.read()
    
    user_prompt = user_template.format(
        section_title=section_data["section_title"],
        narration_segments=segments_text,
        visual_description="Create clear, educational visualization matching narration",
        formulas=", ".join(section_data["formulas"]),
        key_terms=", ".join(section_data["key_terms"]),
        total_duration=section_data["total_duration"],
        special_requirements="Use blue for areas, yellow for curves, maintain visual clarity"
    )
    
    # 4. Call Claude via OpenRouter
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=openrouter_api_key
    )
    
    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4.5",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    
    # 5. Extract Python code
    manim_code = response.choices[0].message.content
    
    # Remove markdown code blocks if present
    if "```python" in manim_code:
        manim_code = manim_code.split("```python")[1].split("```")[0]
    elif "```" in manim_code:
        manim_code = manim_code.split("```")[1]
    
    return manim_code.strip()
```

---

## Step 4: Create Renderer JSON

### Wrap LLM Output in JSON Structure

```python
def create_renderer_json(section_data, manim_code):
    """
    Create JSON structure for Manim renderer API.
    
    Args:
        section_data: Original section data with metadata
        manim_code: Python code from LLM (string)
        
    Returns:
        Dictionary ready to send to renderer
    """
    
    return {
        "sections": [{
            "section_id": str(section_data["section_id"]),
            "prompts": [{
                "prompt": " ".join([s["text"] for s in section_data["narration_segments"]]),
                "manim_code": manim_code  # <-- LLM output goes here
            }]
        }],
        "quality_preset": "preview",  # or "production"
        "use_cache": True
    }
```

### Example: Complete JSON

```json
{
  "sections": [{
    "section_id": "3",
    "prompts": [{
      "prompt": "The definite integral represents...",
      "manim_code": "# Segment 1 (0-5.2s)\naxes = Axes(...)\nself.play(Create(axes), run_time=2)\nself.wait(3.2)\n..."
    }]
  }],
  "quality_preset": "preview",
  "use_cache": true
}
```

---

## Step 5: Send to Manim Renderer

### Submit Render Job

```python
import requests
import time

def render_manim_video(renderer_json, renderer_url="http://localhost:8001"):
    """
    Send JSON to Manim renderer and wait for completion.
    
    Args:
        renderer_json: JSON structure from create_renderer_json()
        renderer_url: URL of Manim renderer service
        
    Returns:
        Path to rendered MP4 video
    """
    
    # 1. Submit job
    response = requests.post(
        f"{renderer_url}/render",
        json=renderer_json
    )
    response.raise_for_status()
    
    job_id = response.json()["job_id"]
    print(f"Job submitted: {job_id}")
    
    # 2. Poll for completion
    while True:
        status_response = requests.get(f"{renderer_url}/status/{job_id}")
        status_data = status_response.json()
        
        status = status_data["status"]
        print(f"Status: {status}")
        
        if status == "finished":
            video_filename = status_data["result"]["filename"]
            print(f"✅ Render complete: {video_filename}")
            
            # 3. Download video
            video_response = requests.get(
                f"{renderer_url}/download/{video_filename}",
                stream=True
            )
            
            output_path = f"output/{video_filename}"
            with open(output_path, "wb") as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return output_path
            
        elif status == "failed":
            error = status_data.get("error", "Unknown error")
            raise Exception(f"Render failed: {error}")
        
        time.sleep(5)  # Wait 5 seconds before checking again
```

---

## Step 6: Complete Pipeline Example

### Put It All Together

```python
def process_section(section_data, openrouter_api_key):
    """
    Complete pipeline: Generate code → Render video
    """
    
    print(f"Processing section: {section_data['section_title']}")
    
    # 1. Generate Manim code with LLM
    print("  Generating Manim code...")
    manim_code = generate_manim_code(section_data, openrouter_api_key)
    
    # 2. Create renderer JSON
    print("  Creating renderer JSON...")
    renderer_json = create_renderer_json(section_data, manim_code)
    
    # Optional: Save JSON for debugging
    with open(f"debug_section_{section_data['section_id']}.json", "w") as f:
        json.dump(renderer_json, f, indent=2)
    
    # 3. Render video
    print("  Rendering video...")
    video_path = render_manim_video(renderer_json)
    
    print(f"  ✅ Complete: {video_path}")
    return video_path


# Usage
if __name__ == "__main__":
    # Your section data (from your existing pipeline)
    section = {
        "section_id": "3",
        "section_title": "Definite Integral",
        "narration_segments": [
            {
                "start": 0,
                "duration": 5.2,
                "text": "The definite integral...",
                "visual": "Show title and axes"
            },
            # ... more segments
        ],
        "total_duration": 20.0,
        "formulas": ["∫ₐᵇ f(x)dx"],
        "key_terms": ["integral symbol", "limits"]
    }
    
    # Process
    video_path = process_section(section, "YOUR_OPENROUTER_API_KEY")
    print(f"Video saved: {video_path}")
```

---

## 📋 Checklist

Before running your pipeline, ensure:

- [ ] Manim renderer is running (`docker-compose up`)
- [ ] You have narration segments with timing (start, duration, text)
- [ ] System prompt loaded from `manim_system_prompt.txt`
- [ ] User prompt uses template from `manim_user_prompt_template.txt`
- [ ] Using Claude Sonnet 4.5 via OpenRouter
- [ ] JSON structure matches renderer API format
- [ ] Quality preset chosen (preview for testing, production for final)

---

## 🎓 Key Points

### Timing Flow

```
Your Narration → Segment Timing → LLM Prompt → Manim Code → Video
    (TTS)         (duration)      (with timing)   (synced)
```

### What Goes Where

| Component | File/Location | Content |
|-----------|---------------|---------|
| **System Prompt** | `prompts/manim_system_prompt.txt` | Rules for Manim code generation |
| **User Prompt** | `prompts/manim_user_prompt_template.txt` | Template with timing placeholders |
| **Narration Timing** | Your pipeline data | Segment start, duration, text |
| **LLM Output** | Python code string | Goes into `manim_code` field |
| **Renderer Input** | JSON file | `render_prompts_CORRECTED.json` format |
| **Renderer Output** | MP4 video | Final rendered animation |

### Quality Presets

- **preview**: Fast rendering (~5x faster), use for testing
- **production**: High quality, use for final videos

---

## 🔍 Debugging

### If Manim Code Has Errors

1. Check LLM output for `Dot()` placeholders → regenerate with clearer prompt
2. Verify timing adds up: sum of (run_time + wait) should equal segment duration
3. Look for variable overwrites (e.g., `axes = axes.plot(...)`)

### If Rendering Fails

1. Check renderer logs: `docker-compose logs worker_1`
2. Test with preview quality first
3. Validate JSON structure matches `render_prompts_CORRECTED.json`

### Example Files

- **Good JSON**: `manim-renderer/sample input/render_prompts_CORRECTED.json`
- **Bad JSON** (for comparison): `manim-renderer/sample input/render_prompts (2).json`

---

**You're ready to generate synchronized Manim videos!** 🚀
