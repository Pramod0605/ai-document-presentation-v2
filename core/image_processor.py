import os
import re
import base64
from pathlib import Path
from PIL import Image
from io import BytesIO

try:
    from rembg import remove as remove_bg
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False
    print("[ImageProcessor] rembg not available - will use basic processing")


def extract_images_from_markdown(md_content: str, output_dir: str) -> dict:
    """
    Extract base64 images from markdown content, save them with green background.
    Returns mapping: {"IMAGE_1": "filename.png", ...}
    """
    os.makedirs(output_dir, exist_ok=True)
    
    base64_pattern = r'!\[([^\]]*)\]\(data:image/(png|jpeg|jpg|gif|webp);base64,([A-Za-z0-9+/=]+)\)'
    
    matches = re.findall(base64_pattern, md_content)
    
    images_mapping = {}
    image_counter = 0
    
    for alt_text, img_format, base64_data in matches:
        image_counter += 1
        img_key = f"IMAGE_{image_counter}"
        
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', alt_text or f"image_{image_counter}")
        filename = f"{safe_name}.png"
        filepath = os.path.join(output_dir, filename)
        
        try:
            img_bytes = base64.b64decode(base64_data)
            img = Image.open(BytesIO(img_bytes))
            
            processed_img = apply_green_background(img)
            
            processed_img.save(filepath, 'PNG')
            
            images_mapping[img_key] = {
                'filename': filename,
                'alt_text': alt_text,
                'path': filepath,
                'width': processed_img.width,
                'height': processed_img.height
            }
            
            print(f"[ImageProcessor] Saved {img_key}: {filename} ({processed_img.width}x{processed_img.height})")
            
        except Exception as e:
            print(f"[ImageProcessor] Error processing {img_key}: {e}")
            continue
    
    print(f"[ImageProcessor] Extracted {len(images_mapping)} images to {output_dir}")
    return images_mapping


def apply_green_background(img: Image.Image) -> Image.Image:
    """
    Apply green background for chroma key effect.
    If rembg available, remove existing background first.
    """
    GREEN = (0, 177, 64, 255)
    
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    if HAS_REMBG:
        try:
            img = remove_bg(img)
            print("[ImageProcessor] Background removed with rembg")
        except Exception as e:
            print(f"[ImageProcessor] rembg failed, using original: {e}")
    
    green_bg = Image.new('RGBA', img.size, GREEN)
    
    composite = Image.alpha_composite(green_bg, img)
    
    return composite.convert('RGB')


def strip_base64_from_markdown(md_content: str) -> str:
    """
    Remove base64 image data from markdown, leaving only text.
    Replaces with IMAGE_X placeholders for LLM.
    """
    base64_pattern = r'!\[([^\]]*)\]\(data:image/[^;]+;base64,[A-Za-z0-9+/=]+\)'
    
    counter = [0]
    
    def replace_with_placeholder(match):
        counter[0] += 1
        alt_text = match.group(1) or f"image_{counter[0]}"
        return f"[IMAGE_{counter[0]}: {alt_text}]"
    
    clean_md = re.sub(base64_pattern, replace_with_placeholder, md_content)
    
    print(f"[ImageProcessor] Replaced {counter[0]} base64 images with placeholders")
    return clean_md


def create_image_list_for_llm(images_mapping: dict) -> str:
    """
    Create a text list of available images for LLM prompt.
    """
    if not images_mapping:
        return "No images available."
    
    lines = ["AVAILABLE IMAGES:"]
    for img_key, info in sorted(images_mapping.items()):
        alt = info.get('alt_text', 'No description')
        lines.append(f"  {img_key}: {alt} ({info['filename']})")
    
    return "\n".join(lines)


if __name__ == "__main__":
    test_md = """
    # Test Document
    Here is an image: ![Test Diagram](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==)
    And some text.
    """
    
    clean = strip_base64_from_markdown(test_md)
    print("Clean markdown:", clean)
