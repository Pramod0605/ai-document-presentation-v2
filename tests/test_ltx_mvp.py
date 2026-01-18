"""
Test LTX MVP
Generates 3 videos with ~80 word prompts to test batching/timing.
"""
import os
import time
import sys
# Add parent dir to path to import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from render.ltx.ltx_client import LtxClient

def test_mvp():
    client = LtxClient()
    
    # Simple check if base URL is accessible
    try:
        print(f"Testing connectivity to {client.base_url}...")
        # Assuming there is a health check or just proceed
    except Exception as e:
        print(f"Connectivity issue: {e}")

    prompts = [
        "A futuristic city with flying cars and neon lights, cinematic lighting, 4k resolution, high detail, bustling streets, cyberpunk aesthetic.",
        "A serene forest with sunlight streaming through the trees, deer grazing, high quality, photorealistic, nature documentary style.",
        "An astronaut floating in deep space, Earth in background, stars, high detail, realistic textures, 8k resolution."
    ]
    
    start_time = time.time()
    
    for i, prompt in enumerate(prompts):
        print(f"\n--- Generating Video {i+1}/3 ---")
        p_start = time.time()
        try:
            output = client.generate_video(prompt, output_path=f"ltx_test_{i+1}.mp4")
            duration = time.time() - p_start
            print(f"Success! Saved to {output} in {duration:.2f}s")
        except Exception as e:
            print(f"Failed: {e}")
            
    total_time = time.time() - start_time
    print(f"\nTotal Time: {total_time:.2f}s")

if __name__ == "__main__":
    test_mvp()
