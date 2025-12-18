# Image Handling & Display Workflow

This document explains how images flow through the video generation pipeline - from PDF extraction to final display in slides.

## Overview

Images are **NOT sent to the LLM** for content generation. Instead:
1. Images are extracted from PDF via Datalab JSON
2. Placeholder references (IMAGE_1, IMAGE_2, etc.) are used in the LLM prompt
3. The LLM assigns image placeholders to slides without seeing the actual images
4. Images are saved as files and linked in the final HTML slides

## Step 1: PDF to Datalab JSON Extraction

Datalab API extracts images from the PDF and embeds them as base64 in the JSON output:

```json
{
  "block_type": "Picture",
  "id": "/page/0/Picture/12",
  "images": {
    "Binary-Fission-diagram.png": "iVBORw0KGgoAAAANSUhEUgAAA..."
  },
  "bbox": [50, 200, 400, 350]
}
```

**Key fields:**
- `block_type: "Picture"` - Identifies image blocks
- `images: {filename: base64_data}` - Actual image data
- `bbox` - Bounding box coordinates (used for size)

## Step 2: Parsing Images (DatalabParser)

The `agents/datalab_parser.py` extracts image blocks into structured data:

```python
# From agents/datalab_parser.py
def _parse_picture(self, images: Dict, bbox: List) -> Dict:
    """Parse Picture block with base64 image data."""
    image_data = None
    image_name = None
    
    # Get first image from the images dict
    for name, data in images.items():
        image_name = name
        image_data = data
        break
    
    return {
        'image_name': image_name,
        'image_base64': image_data,  # Stored for later file save
        'width': bbox[2] - bbox[0] if len(bbox) >= 4 else 0,
        'height': bbox[3] - bbox[1] if len(bbox) >= 4 else 0,
        'sentences': []  # Images have no sentences for narration
    }
```

## Step 3: Creating Placeholder References for LLM

Images are **NOT sent to the LLM**. Instead, we create placeholder references:

```python
# From run_v3_combined.py - extract_images_from_json()
def extract_images_from_json(json_data: Dict) -> tuple:
    """
    Extract image references from datalab JSON with actual filenames.
    Returns (images_list_for_prompt, images_mapping_dict)
    
    images_mapping_dict maps IMAGE_1, IMAGE_2, etc. to actual filenames.
    """
    images_list = []
    images_mapping = {}
    
    def process_block(block: Dict) -> None:
        block_type = block.get('block_type', block.get('type', ''))
        
        if block_type == 'Picture':
            block_id = block.get('id', '')
            images_dict = block.get('images', {})
            
            if images_dict and isinstance(images_dict, dict):
                for filename, base64_data in images_dict.items():
                    img_num = len(images_list) + 1
                    img_key = f"IMAGE_{img_num}"  # Placeholder key
                    
                    # Store filename reference (NOT the actual image data)
                    images_list.append(f"{img_key}: {filename}")
                    images_mapping[img_key] = {
                        'filename': filename,
                        'block_id': block_id,
                        'has_data': bool(base64_data)
                    }
```

**Result:**
- `images_list` = `["IMAGE_1: Binary-Fission-diagram.png", "IMAGE_2: Cell-Division.jpg"]`
- `images_mapping` = `{"IMAGE_1": {"filename": "Binary-Fission-diagram.png", ...}}`

## Step 4: LLM Prompt with Placeholders (NOT Image Data)

The LLM receives only the placeholder list, not actual images:

```python
# From run_v3_combined.py - call_combined_llm()
prompts = load_prompt('combined_slides', {
    'topic': topic,
    'content': clean_markdown_content,
    'images_list': images_list  # Just "IMAGE_1: filename.png" text
})
```

**What the LLM sees:**
```
AVAILABLE IMAGES:
IMAGE_1: Binary-Fission-diagram.png
IMAGE_2: Cell-Division.jpg
IMAGE_3: Bacteria-types.png

Your task: Assign appropriate images to slides using IMAGE_X references...
```

**LLM output:**
```json
{
  "slides": [
    {
      "slide_type": "content",
      "title": "Binary Fission",
      "image_id": "IMAGE_1"  // Just the placeholder reference
    }
  ]
}
```

## Step 5: Saving Images to Disk

Images are saved from base64 to actual files:

```python
# From run_v3_combined.py - save_images_from_json()
def save_images_from_json(json_data: Dict, output_dir: str) -> Dict:
    """Save all images from JSON to disk, return IMAGE_X -> filename mapping."""
    saved_images = {}
    image_counter = [0]
    
    def process_block(block: Dict):
        if block_type == 'Picture':
            images_dict = block.get('images', {})
            
            for filename, base64_data in images_dict.items():
                if base64_data:
                    # Decode and save actual image file
                    img_data = base64.b64decode(base64_data)
                    img_path = os.path.join(output_dir, filename)
                    with open(img_path, 'wb') as f:
                        f.write(img_data)
                    
                    image_counter[0] += 1
                    img_key = f"IMAGE_{image_counter[0]}"
                    saved_images[img_key] = filename
                    print(f"  Saved {img_key}: {filename}")
    
    return saved_images
```

**Output folder structure:**
```
output/v3/{job_id}/
├── images/
│   ├── Binary-Fission-diagram.png   ← Actual file
│   ├── Cell-Division.jpg            ← Actual file
│   └── recap/
│       ├── scene_01.png
│       └── scene_02.png
```

## Step 6: Resolving IMAGE_X to Actual Filenames

After LLM returns slides, we replace placeholders with real filenames:

```python
# From run_v3_combined.py - post-processing
print(f"  Mapping image references to filenames...")
for slide in slides:
    img_id = slide.get('image_id')
    if img_id and img_id.startswith('IMAGE_'):
        if img_id in images_mapping:
            # Replace placeholder with actual filename
            slide['image_filename'] = images_mapping[img_id]['filename']
```

**Before:**
```json
{"title": "Binary Fission", "image_id": "IMAGE_1"}
```

**After:**
```json
{"title": "Binary Fission", "image_id": "IMAGE_1", "image_filename": "Binary-Fission-diagram.png"}
```

## Step 7: HTML Template Rendering

The slide template displays the image using the resolved filename:

```python
# From run_v3_combined.py - render_slide()
context = {
    'slide_number': slide_num,
    'title': slide.get('title', ''),
    'image_id': image_filename,  # The resolved filename
    'image_base_url': '../images',
    ...
}
```

**Template (templates/slide_v3_content.html):**
```html
<div class="content-area">
    <h1 class="title">{{ title }}</h1>
    
    {% if image_id %}
    <img class="slide-image" 
         src="{{ image_base_url }}/{{ image_id }}" 
         alt="Slide image">
    {% endif %}
    
    <div class="segments">
        {% for segment in segments %}
        <p class="segment" data-start="{{ segment.start_time }}">
            {{ segment.text }}
        </p>
        {% endfor %}
    </div>
</div>
```

**Rendered HTML:**
```html
<img class="slide-image" 
     src="../images/Binary-Fission-diagram.png" 
     alt="Slide image">
```

## Image Enhancement (Optional)

The `ImageEnhancerAgent` can enhance or generate new images:

```python
# From agents/image_enhancer_agent.py
class ImageEnhancerAgent(BaseAgent):
    
    def enhance_image(self, image_path: str, output_path: str, context: str = None):
        """Enhance an existing image using AI"""
        # Read original image as base64
        with open(image_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Call Gemini to enhance
        enhanced_path = self.generate_image(
            prompt=f"Enhance this educational diagram: {context}",
            output_path=output_path
        )
        return enhanced_path
    
    def generate_infographic(self, slide: Dict, output_path: str):
        """Generate new infographic for slides without images"""
        title = slide.get('detected_title', 'Concept')
        bullets = slide.get('detected_bullets', [])
        
        prompt = f"""Create a professional infographic.
        TOPIC: {title}
        KEY POINTS: {'. '.join(bullets)}
        """
        
        return self.generate_image(prompt, output_path)
```

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PDF INPUT                                       │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATALAB API EXTRACTION                                │
│                                                                              │
│  Input: biology.pdf                                                          │
│  Output: biology_datalab.json                                                │
│          - Text blocks                                                       │
│          - Images as base64 in "images" dict                                │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      EXTRACT IMAGE REFERENCES                                │
│                                                                              │
│  Function: extract_images_from_json()                                        │
│                                                                              │
│  Creates placeholder mapping:                                                │
│    IMAGE_1 → "Binary-Fission.png"                                           │
│    IMAGE_2 → "Cell-Division.jpg"                                            │
│                                                                              │
│  ⚠️ IMAGES NOT SENT TO LLM - Only placeholder text                          │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LLM SLIDE GENERATION                                 │
│                                                                              │
│  Prompt includes:                                                            │
│    "AVAILABLE IMAGES:                                                        │
│     IMAGE_1: Binary-Fission.png                                             │
│     IMAGE_2: Cell-Division.jpg"                                             │
│                                                                              │
│  LLM assigns: slide.image_id = "IMAGE_1"                                    │
│  (Based on filename context, NOT seeing actual image)                       │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SAVE IMAGES TO DISK                                  │
│                                                                              │
│  Function: save_images_from_json()                                           │
│                                                                              │
│  For each Picture block:                                                     │
│    1. Decode base64 data                                                     │
│    2. Write to output/v3/{job}/images/{filename}                            │
│    3. Track IMAGE_X → filename mapping                                      │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       RESOLVE IMAGE REFERENCES                               │
│                                                                              │
│  For each slide:                                                             │
│    if slide.image_id == "IMAGE_1":                                          │
│        slide.image_filename = "Binary-Fission.png"                          │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RENDER HTML TEMPLATES                                 │
│                                                                              │
│  Template receives:                                                          │
│    image_id = "Binary-Fission.png"                                          │
│    image_base_url = "../images"                                              │
│                                                                              │
│  Renders:                                                                    │
│    <img src="../images/Binary-Fission.png">                                 │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FINAL OUTPUT                                         │
│                                                                              │
│  output/v3/{job_id}/                                                         │
│  ├── html/                                                                   │
│  │   ├── slide_001.html  ← References ../images/                            │
│  │   └── slide_002.html                                                      │
│  ├── images/                                                                 │
│  │   ├── Binary-Fission.png  ← Actual image file                           │
│  │   └── Cell-Division.jpg                                                   │
│  └── presentation_player.html                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `agents/datalab_parser.py` | Parse Datalab JSON, extract image blocks |
| `run_v3_combined.py` | Main pipeline - extract_images_from_json(), save_images_from_json() |
| `agents/image_enhancer_agent.py` | Optional image enhancement/generation |
| `templates/slide_v3_content.html` | HTML template with image display |

## Why Images Are NOT Sent to LLM

1. **Token limits**: Base64 images would consume massive token counts
2. **Cost**: Image tokens are expensive
3. **Speed**: Sending images slows down requests significantly
4. **Not needed**: LLM only needs to know WHICH image goes WHERE, not see it

The LLM infers image relevance from:
- Filename (e.g., "Binary-Fission.png" suggests binary fission content)
- Position in document (images near related text)
- Caption blocks (if present)
