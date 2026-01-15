import sys
import os
import json
from dotenv import load_dotenv

# Add parent directory to path to import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.unified_content_generator import call_openrouter_llm, extract_json_from_response, GeneratorConfig

# Load env for API keys (Force override to ensure we get the file value, not stale system var)
load_dotenv(override=True)

def test_director_prompt():
    print("Starting Director Prompt Test (Live LLM Call)...")
    
    # 1. Load the Updated Prompt
    prompt_path = "core/prompts/director_partition_prompt.txt"
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
        print(f"Loaded System Prompt from {prompt_path}")
    except FileNotFoundError:
        print(f"Error: Could not find {prompt_path}")
        return

    # 2. Define the "Problematic" Narrative Input (Section 3 Intro)
    # This is the text that previously generated a "Wall of Text" visual beat
    test_chunk_content = """
The chapter “The Human Eye and the Colourful World” explains how we are able to see objects around us and why nature appears colourful. The human eye is a sensitive and important sense organ that uses light to form images of objects. Just like a camera, the eye has a lens system that focuses light on a screen called the retina.

In this chapter, we apply the ideas of refraction of light (studied in the previous chapter) to understand the structure and working of the human eye, various defects of vision and their correction using lenses. The chapter also explains several beautiful natural phenomena such as formation of rainbow, dispersion of white light, blue colour of the sky, twinkling of stars, and advance sunrise and delayed sunset.
"""
    
    chunk_title = "Chapter Introduction (Narrative Test)"
    grade = "Grade 10"
    subject = "Science"
    
    # Construct User Prompt
    user_prompt = (
        f"SUBJECT: {subject}\n"
        f"Target Chunk Title: {chunk_title}\n\n"
        f"=== FULL DOCUMENT CONTEXT (Read Only) ===\n{test_chunk_content}\n\n" # Using same as context for simplicity
        f"=== AVAILABLE IMAGES (Usage Mandatory if relevant) ===\n[]\n\n"
        f"=== TARGET CHUNK (VISUALIZE THIS) ===\n{test_chunk_content}\n\n"
        f"Instructions: Create slides for the TARGET CHUNK only. Use images from the list above."
    )

    print("\nSending Request to LLM... (This may take 10-20s)")
    
    # 3. Call LLM
    config = GeneratorConfig()
    # Ensure a smart model is used (Or use default from env)
    # config.model = "google/gemini-2.0-flash-exp" 
    
    try:
        response, _ = call_openrouter_llm(system_prompt, user_prompt, config)
        data = extract_json_from_response(response)
        
        print("\nLLM Response Received!")
        print("-" * 50)
        
        # 4. Analyze Visual Beats
        sections = data.get("sections", [])
        if not sections:
            print("No sections generated.")
            return

        for sec in sections:
            print(f"\nSection: {sec.get('title')}")
            beats = sec.get("visual_beats", [])
            print(f"Visual Beats Generated: {len(beats)}")
            
            for i, beat in enumerate(beats):
                v_type = beat.get("visual_type")
                d_text = beat.get("display_text", "")
                pointer = beat.get("markdown_pointer", {})
                
                print(f"  [{i+1}] Type: {v_type}")
                print(f"      Text Length: {len(d_text)} chars")
                print(f"      Start Phrase: '{pointer.get('start_phrase')}'")
                print(f"      Display Text: {d_text[:100]}..." if len(d_text) > 100 else f"      Display Text: {d_text}")
                
                if len(d_text) > 200 and v_type == "text":
                     print("      WARNING: Long text detected! (Potential Wall of Text)")
                elif v_type in ["bullet_list", "image", "diagram"]:
                     print("      GOOD: Structured Visual Beat")
                elif len(d_text) < 100:
                     print("      GOOD: Concise Text")

    except Exception as e:
        print(f"LLM Call Failed: {e}")

if __name__ == "__main__":
    test_director_prompt()
