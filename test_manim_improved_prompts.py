"""
Test Improved Manim Prompts with Real Production Job Data

This script tests the V2.6 prompt design against job 3181b28d Section 3.
It now loads prompts from the actual files (core/prompts/) to test production behavior.
"""
import os
import sys
import json
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# CRITICAL: Force reload .env with override=True (same as working tests)
from dotenv import load_dotenv
load_dotenv(override=True)

# Import the WORKING LLM call function
from core.unified_content_generator import call_openrouter_llm, GeneratorConfig

# Load prompts from actual files (now with V2.6 improvements)
PROMPTS_DIR = Path(__file__).parent / "core" / "prompts"

with open(PROMPTS_DIR / "manim_system_prompt_v25.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()
    print(f"[TEST] Loaded system prompt: {len(SYSTEM_PROMPT)} chars")

with open(PROMPTS_DIR / "manim_user_prompt_v25.txt", "r", encoding="utf-8") as f:
    USER_PROMPT_TEMPLATE = f.read()
    print(f"[TEST] Loaded user prompt template: {len(USER_PROMPT_TEMPLATE)} chars")

IMPROVED_SYSTEM_PROMPT = """You are a senior Manim expert and Python developer. 
Your task is to generate a **COMPLETE, EXECUTABLE Python script** for a Manim animation.

=== SYSTEM ARCHITECTURE ===
- **Output Format**: A single, valid Python file (.py).
- **Execution**: The user will run `manim -q l scene.py MainScene` directly.
- **No Wrapping**: Do NOT assume your code will be wrapped. YOU must include all imports and the class definition.

=== CRITICAL REQUIREMENTS ===
1. **Modules**: Start with `from manim import *`.
2. **Class**: Define a class named `MainScene(Scene)`.
3. **Method**: Implement `def construct(self):`.
4. **NO MARKDOWN**: Output PURE PYTHON CODE ONLY. Do not use ```python``` blocks.

=== TEXT AND ENCODING RULES (CRITICAL) ===
- **ASCII-ONLY TEXT**: Non-ASCII characters cause Manim crashes.
- Use ASCII replacements: Rs., -, ..., " ", x, /, degrees
- All Text() and MathTex() content MUST be pure ASCII.

=== MANIM v0.19.0 RULES ===
- Use `Axes` (not `NumberPlane` for graphs).
- Use `MathTex` (not `TexMobject`). Use `Text` (not `TextMobject`).
- Use `Create()`, `Write()`, `FadeIn()`, `FadeOut()`.

**COLORS**:
- Use ONLY: RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE, PINK, TEAL, GOLD, MAROON, GRAY, WHITE, BLACK.
- For other colors, use Hex Strings (e.g., color="#8B4513").

=== VISUAL QUALITY FLOOR (REQUIRED) ===

Every segment MUST have meaningful visual activity, not just text.

MINIMUM REQUIREMENTS per segment:
- At least ONE geometric object OR equation (not just plain Text)
- At least ONE animation effect (movement, transformation, or highlight)
- Distribute run_time across the segment (not just start + long wait)

=== TIMING DISTRIBUTION (NON-NEGOTIABLE) ===

BAD PATTERN (avoid):
  self.play(Write(x), run_time=2.0)
  self.wait(25.0)  # 90% dead time

GOOD PATTERN (use this):
  self.play(Write(x), run_time=2.0)
  self.wait(2.0)
  self.play(Indicate(x), run_time=1.0)
  self.wait(5.0)
  self.play(x.animate.scale(1.1), run_time=1.5)
  self.wait(5.0)
  self.play(Circumscribe(x), run_time=1.0)
  self.wait(8.5)
  self.play(FadeOut(x), run_time=1.0)

=== MANIM ANIMATION PATTERNS (USE THESE) ===

PATTERN A: LABELED TRIANGLE
  A, B, C = ORIGIN, RIGHT*3, RIGHT*3 + UP*2.25
  triangle = Polygon(A, B, C, color=WHITE)
  label_a = MathTex("A").next_to(A, DOWN+LEFT, buff=0.2)
  self.play(Create(triangle), run_time=1.5)
  self.play(Write(label_a), run_time=1.0)

PATTERN B: SIDE LABELS WITH BRACE
  side = Line(B, C)
  brace = Brace(side, direction=RIGHT)
  brace_text = brace.get_tex("4")
  self.play(Create(brace), Write(brace_text), run_time=1.0)

PATTERN C: HIGHLIGHT FORMULA PARTS
  formula = MathTex(r"\\sin A = \\frac{Opp}{Hyp}")
  box = SurroundingRectangle(formula, color=YELLOW, buff=0.1)
  self.play(Write(formula), run_time=2.0)
  self.play(Create(box), run_time=0.5)
  self.wait(2.0)
  self.play(FadeOut(box), run_time=0.3)

PATTERN D: STEP-BY-STEP CALCULATION
  step1 = MathTex(r"AC^2 = AB^2 + BC^2").to_edge(UP)
  step2 = MathTex(r"AC^2 = 3^2 + 4^2").to_edge(UP)
  self.play(Write(step1), run_time=1.5)
  self.wait(2.0)
  self.play(TransformMatchingTex(step1, step2), run_time=1.0)

PATTERN E: INDICATE IMPORTANT ELEMENTS
  self.play(Indicate(triangle), color=YELLOW, run_time=0.8)
  self.wait(1.5)

=== SEGMENT ISOLATION (MANDATORY) ===

Every segment MUST end with cleanup:
  self.play(FadeOut(*self.mobjects), run_time=0.5)

The screen MUST be empty at the start of every segment.

=== OUTPUT FORMAT ===

At the END of each segment block, include:
# Segment X (Y.Ys)

Use the EXACT duration provided in the narration.
"""

IMPROVED_USER_PROMPT_TEMPLATE = """Generate a complete, executable Manim script for the following section.

**Section Title**: {section_title}

=== NARRATION SCHEDULE (Use strictly for timing) ===
{narration_segments}

=== VISUAL SCENE DESCRIPTION (MATCH THIS CLOSELY) ===
{visual_description}

You MUST include the key visual elements described above.
- If the description mentions "labeled", add Text/MathTex labels
- If the description mentions "highlight" or "glow", use Indicate() or SurroundingRectangle
- If the description mentions "animation" or "movement", use .animate or Transform

=== MATHEMATICAL CONTENT ===
- Main formulas: {formulas}
- Key terms: {key_terms}

=== GENERATION CONSTRAINTS ===
1. **Timing**: Total run_time + wait MUST equal Segment Duration exactly.
2. **Distribution**: Do NOT have wait() > 10 seconds. Fill time with Indicate(), subtle .animate movements.
3. **Cleanup**: End EVERY segment with FadeOut(*self.mobjects) or self.clear().
4. **Encoding**: Use ASCII text only. NO Unicode symbols.
5. **Output**: Return PURE PYTHON CODE ONLY. No markdown, no explanations.
"""

# ============================================================================
# TEST DATA - Real segments from job 3181b28d Section 3 (subset for testing)
# ============================================================================

TEST_SECTION_DATA = {
    "section_title": "Introduction to Trigonometry and Ratios",
    "narration_segments": [
        {
            "segment_id": "seg_2",
            "text": "Now, watch this. See how as the angle changes, the lengths of the sides also change? This relationship is the heart of trigonometry.",
            "duration_seconds": 11.68,
            "duration": 11.68
        },
        {
            "segment_id": "seg_4", 
            "text": "Here we see a right-angled triangle. The longest side, always opposite the 90-degree angle, is the Hypotenuse. Relative to our angle, which we'll call A, the side directly across from it is the Opposite side, and the side right next to it is the Adjacent side.",
            "duration_seconds": 27.42,
            "duration": 27.42
        },
        {
            "segment_id": "seg_6",
            "text": "Let's see how these ratios are formed. For Sin A, we take the Opposite and divide by the Hypotenuse. For Cos A, it's the Adjacent over the Hypotenuse. And for Tan A, it's the Opposite over the Adjacent.",
            "duration_seconds": 23.86,
            "duration": 23.86
        }
    ],
    "manim_spec": """
Segment 1: Display a right-angled triangle with vertices labeled A, B, C. The right angle is at B. Show angle A with a yellow arc. Create subtle pulsing or scaling effects to demonstrate the relationship between angle and sides.

Segment 2: Display a bright yellow right-angled triangle clearly labeled. Mark the right angle. Show the labels 'Hypotenuse', 'Opposite side', and 'Adjacent side' appearing one by one with highlight effects on each corresponding side.

Segment 3: Show the triangle with formulas appearing one by one. For sin A = Opposite/Hypotenuse, highlight the Opposite side for numerator, then Hypotenuse for denominator. Repeat for cos A and tan A.
""",
    "visual_description": "Right-angled triangle with labeled sides showing trigonometric ratios",
    "formulas": ["sin A = Opposite/Hypotenuse", "cos A = Adjacent/Hypotenuse", "tan A = Opposite/Adjacent"],
    "key_terms": ["Hypotenuse", "Opposite", "Adjacent", "Trigonometric Ratios"]
}


def format_segments_for_prompt(segments):
    """Format narration segments for the prompt."""
    lines = []
    current_time = 0.0
    
    for i, seg in enumerate(segments, 1):
        duration = seg.get("duration_seconds") or seg.get("duration", 5.0)
        text = seg.get("text", "")
        end_time = current_time + duration
        
        lines.append(f"Segment {i} ({current_time:.1f}s - {end_time:.1f}s, duration {duration:.1f}s):")
        lines.append(f'  Narration: "{text}"')
        lines.append("")
        
        current_time = end_time
    
    return "\n".join(lines)


def build_user_prompt(section_data):
    """Build the user prompt from section data using V2.6 template from file."""
    narration_text = format_segments_for_prompt(section_data["narration_segments"])
    
    visual_desc = section_data.get("manim_spec", section_data.get("visual_description", ""))
    formulas = ", ".join(section_data.get("formulas", [])) or "None"
    key_terms = ", ".join(section_data.get("key_terms", [])) or "None"
    
    # Use template from actual file
    return USER_PROMPT_TEMPLATE.format(
        section_title=section_data["section_title"],
        narration_segments=narration_text,
        visual_description=visual_desc,
        formulas=formulas,
        key_terms=key_terms
    )


def generate_with_improved_prompts(section_data):
    """Generate Manim code using call_openrouter_llm with V2.6 prompts from files."""
    user_prompt = build_user_prompt(section_data)
    
    # Use GeneratorConfig but override for Manim generation
    config = GeneratorConfig()
    config.model = "google/gemini-2.5-flash"  # Fast model for testing
    config.max_tokens = 8192
    config.temperature = 0.3
    
    print(f"[TEST] Generating Manim code with V2.6 prompts from files...")
    print(f"[TEST] Model: {config.model}")
    print(f"[TEST] System prompt: {len(SYSTEM_PROMPT)} chars")
    print(f"[TEST] User prompt: {len(user_prompt)} chars")
    
    try:
        # Use SYSTEM_PROMPT loaded from actual file
        response, usage = call_openrouter_llm(SYSTEM_PROMPT, user_prompt, config)
        print(f"[TEST] Response received: {len(response)} chars")
        print(f"[TEST] Usage: {usage}")
        
        # Extract code from markdown if present
        code = response.strip()
        if "```python" in code:
            import re
            match = re.search(r"```python\s*(.*?)\s*```", code, re.DOTALL)
            if match:
                code = match.group(1)
        elif "```" in code:
            import re
            match = re.search(r"```\s*(.*?)\s*```", code, re.DOTALL)
            if match:
                code = match.group(1)
        
        return code.strip(), []
        
    except Exception as e:
        print(f"[TEST] LLM call failed: {e}")
        return None, [str(e)]


def render_manim(code, output_dir):
    """Render the Manim code to a video."""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Save code to temp file
    code_file = output_dir / "test_scene.py"
    with open(code_file, "w", encoding="utf-8") as f:
        f.write(code)
    
    print(f"[TEST] Saved code to: {code_file}")
    print(f"[TEST] Code length: {len(code)} chars, {len(code.split(chr(10)))} lines")
    
    # Run Manim
    cmd = [
        "manim",
        "-q", "l",  # Low quality for fast testing
        "--disable_caching",
        str(code_file),
        "MainScene"
    ]
    
    print(f"[TEST] Running: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd,
        cwd=str(output_dir),
        capture_output=True,
        text=True,
        timeout=180
    )
    
    if result.returncode != 0:
        print(f"[TEST] RENDER FAILED!")
        print(f"[TEST] STDERR:\n{result.stderr[-2000:]}")
        return None, result.stderr
    
    # Find the output file
    media_dir = output_dir / "media" / "videos" / "test_scene"
    for quality_dir in media_dir.glob("*"):
        video_file = quality_dir / "MainScene.mp4"
        if video_file.exists():
            print(f"[TEST] SUCCESS! Video: {video_file}")
            return str(video_file), None
    
    print(f"[TEST] Video not found in {media_dir}")
    return None, "Video file not found"


def main():
    print("=" * 60)
    print("MANIM PROMPT IMPROVEMENT TEST")
    print("Using call_openrouter_llm (same as working tests)")
    print("=" * 60)
    print()
    
    # Debug: Show API key (masked)
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if api_key:
        print(f"[TEST] API Key: {api_key[:15]}...{api_key[-5:]}")
    else:
        print("[TEST] WARNING: No API key found!")
    
    # Setup output directory
    output_dir = Path(__file__).parent / "temp_manim_test"
    output_dir.mkdir(exist_ok=True)
    
    # Save prompts for inspection
    with open(output_dir / "improved_system_prompt.txt", "w", encoding="utf-8") as f:
        f.write(IMPROVED_SYSTEM_PROMPT)
    with open(output_dir / "improved_user_prompt.txt", "w", encoding="utf-8") as f:
        f.write(build_user_prompt(TEST_SECTION_DATA))
    
    print(f"[TEST] Saved prompts to: {output_dir}")
    print()
    
    # Generate code
    code, errors = generate_with_improved_prompts(TEST_SECTION_DATA)
    
    if not code:
        print(f"[TEST] Failed to generate code! Errors: {errors}")
        return
    
    # Save generated code
    with open(output_dir / "generated_code.py", "w", encoding="utf-8") as f:
        f.write(code)
    print(f"[TEST] Saved generated code to: {output_dir / 'generated_code.py'}")
    print()
    
    # Show code preview
    lines = code.split("\n")
    print("[TEST] Generated code preview (first 60 lines):")
    print("-" * 40)
    for line in lines[:60]:
        print(line)
    print("-" * 40)
    print(f"... ({len(lines)} total lines)")
    print()
    
    # Render video
    print("[TEST] Attempting to render...")
    video_path, error = render_manim(code, str(output_dir))
    
    if video_path:
        print()
        print("=" * 60)
        print("SUCCESS!")
        print(f"Video rendered at: {video_path}")
        print("=" * 60)
        
        # Copy to project root for easy access
        import shutil
        final_path = Path(__file__).parent / "test_manim_improved_output.mp4"
        if Path(video_path).exists():
            shutil.copy(video_path, final_path)
            print(f"Copied to: {final_path}")
    else:
        print()
        print("=" * 60)
        print("RENDER FAILED")
        print(f"Error: {error[:1000] if error else 'Unknown'}")
        print("=" * 60)
        print()
        print("The generated code may have issues. Check temp_manim_test/generated_code.py")


if __name__ == "__main__":
    main()
