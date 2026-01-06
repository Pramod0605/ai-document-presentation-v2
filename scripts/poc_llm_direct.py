
import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load env before imports that might use it
load_dotenv(override=True)

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.unified_content_generator import call_openrouter_llm, GeneratorConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("=" * 60)
    print("POC: DIRECT LLM OUTPUT TEST (V2.5 DIRECTOR)")
    print("=" * 60)

    # 1. Load Prompt
    prompt_path = Path("core/prompts/director_partition_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt_template = f.read()

    print(f"[INFO] Loaded System Prompt ({len(system_prompt_template)} chars)")

    # 2. Define Input (Mock Chunk)
    mock_chunk_content = """
## Potential and Kinetic Energy
In a roller coaster, energy constantly transforms between potential and kinetic forms.
- **Potential Energy (PE)**: Stored energy based on height. $PE = mgh$.
- **Kinetic Energy (KE)**: Energy of motion. $KE = \\frac{1}{2}mv^2$.
    """
    
    mock_full_context = mock_chunk_content

    # 3. Construct Messages
    # The system prompt in the file is actually a template? No, it looks static in the file I viewed. 
    # Let's check if it needs formatting. The viewer showed it as static text "You are an expert...".
    # Wait, the code usually injects context/target into the USER message.
    
    # Let's look at how partition_director_generator.py constructs it.
    # It does:
    # user_msg = f"FULL DOCUMENT CONTEXT:\n{context}\n\nTARGET CHUNK TO VISUALIZE:\n{chunk_text}"
    
    user_msg = f"FULL DOCUMENT CONTEXT:\n{mock_full_context}\n\nTARGET CHUNK TO VISUALIZE:\n{mock_chunk_content}"
    
    # messages = [ ... ] # construct internally by the function
    
    print("[INFO] Calling LLM (google/gemini-2.5-flash)...")
    
    config = GeneratorConfig()
    config.model = "google/gemini-2.5-flash" # EXPLICITLY SET MODEL TO FLASH which works
    
    try:
        response_text, usage = call_openrouter_llm(system_prompt_template, user_msg, config)
        print("\n" + "=" * 60)
        print("RAW LLM RESPONSE:")
        print("=" * 60)
        print(response_text)
        print("=" * 60 + "\n")

        # 4. Parse & Verify
        # Basic cleanup if needed (markdown fences)
        clean_text = response_text.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(clean_text)
        sections = data.get("sections", [])
        
        print(f"[INFO] Parsed JSON. Sections: {len(sections)}")
        
        for i, section in enumerate(sections):
            print(f"\n--- Section {i+1} ({section.get('section_type')}) ---")
            
            # Check Manim Spec
            manim_spec = section.get("manim_scene_spec")
            if not manim_spec:
                manim_spec = section.get("render_spec", {}).get("manim_scene_spec")
            
            print(f"manim_scene_spec TYPE: {type(manim_spec)}")
            
            if isinstance(manim_spec, str):
                print(f"CONTENT: {manim_spec[:100]}...")
                print(f"WORD COUNT: {len(manim_spec.split())}")
            elif isinstance(manim_spec, dict):
                print(f"KEYS: {list(manim_spec.keys())}")
            else:
                print(f"VALUE: {manim_spec}")

    except Exception as e:
        print(f"\n[ERROR] POC Failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"[ERROR DETAILS] Response Status: {e.response.status_code}")
             print(f"[ERROR DETAILS] Response Text: {e.response.text}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
