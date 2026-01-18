
import sys
import os

# Ensure we can import from the core module
sys.path.append(os.getcwd())

from core.wan_prompt_validator import validate_video_prompts, hard_fail_on_short_prompts, WanPromptHardFailError

print("=== TESTING WAN VALIDATOR FIX ===")

# Simulate the data structure causing the issue: 
# A dict with 'wan_prompt' but NO 'prompt' key.
# This previously caused 0 chars / Empty prompt error.
simulated_bad_data = [
    {"wan_prompt": "A cinematic shot of a futuristic city with flying cars and neon lights, rendered in high definition 8k resolution with detailed textures.", "duration_seconds": 5},
    {"text": "Another valid prompt stored under the 'text' key key which was also failing before.", "duration_seconds": 5}
]

print(f"\n[INPUT] Simulating 'bad' data (no 'prompt' key):")
print(simulated_bad_data)

# Test 1: soft validation
print("\n--- Test 1: validate_video_prompts (Soft Check) ---")
is_valid, errors, warn = validate_video_prompts(simulated_bad_data)
if is_valid:
    print("✅ SUCCESS: Validator correctly extracted text from 'wan_prompt'/'text' keys.")
else:
    print(f"❌ FAILURE: Validator failed with errors: {errors}")

# Test 2: hard fail check (Production Check)
print("\n--- Test 2: hard_fail_on_short_prompts (Production Check) ---")
try:
    hard_fail_on_short_prompts(simulated_bad_data, section_id=99, min_words=10) # Low min_words for test
    print("✅ SUCCESS: hard_fail passed! Code is robust.")
except WanPromptHardFailError as e:
    print(f"❌ FAILURE: hard_fail raised error: {e}")
    print("   (This means the fix is NOT working)")
except Exception as e:
    print(f"❌ CRASH: Unexpected error: {e}")

print("\n=== VERIFICATION COMPLETE ===")
