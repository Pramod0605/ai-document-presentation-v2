
import json
import os

JSON_PATH = r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\48808436\presentation.json"

def analyze_prompts():
    if not os.path.exists(JSON_PATH):
        print("ERROR: presentation.json not found")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    sections = data.get("sections", [])
    with open("prompt_quality_report.txt", "w", encoding="utf-8") as outfile:
        outfile.write(f"{'SEC':<4} {'TYPE':<10} {'RENDERER':<8} {'SEGMENTS':<5} {'PROMPTS':<5} {'PLACEHOLDERS':<12} {'QUALITY'}\n")
        outfile.write("-" * 80 + "\n")

        total_placeholders = 0
        total_short_prompts = 0

        for sec in sections:
            sid = sec.get("section_id")
            stype = sec.get("section_type")
            renderer = sec.get("renderer")
            
            # Collect all prompts in this section
            prompts = []
            
            # 1. From video_prompts (top level or legacy)
            if sec.get("video_prompts"):
                for p in sec.get("video_prompts"):
                    prompts.append(p.get("prompt", ""))

            # 2. From render_spec.segment_specs (Manim or WAN specialized)
            if sec.get("render_spec"):
                specs = sec.get("render_spec", {}).get("segment_specs", [])
                for s in specs:
                    # Manim spec
                    if s.get("manim_scene_spec"):
                        prompts.append(s.get("manim_scene_spec"))
                    # Video prompt
                    if s.get("video_prompt"):
                        prompts.append(s.get("video_prompt"))
                    # Beats
                    if s.get("beats"):
                        for b in s.get("beats"):
                            prompts.append(b.get("prompt", ""))

            # 3. From narration.segments (inline beat_videos usually don't have text, but let's check legacy structure)
            # (Skipping deep narration scan as usually prompts are in the above fields for V2.5)

            num_segments = len(sec.get("narration", {}).get("segments", []))
            num_prompts = len(prompts)
            
            placeholders = 0
            short_prompts = 0 # < 20 words
            
            for p in prompts:
                if not p: continue
                if "Cinematic educational visualization" in p:
                    placeholders += 1
                if len(p.split()) < 20:
                    short_prompts += 1

            total_placeholders += placeholders
            total_short_prompts += short_prompts
            
            quality = "OK"
            if placeholders > 0:
                quality = f"⚠️ {placeholders} Default(s)"
            elif num_prompts == 0 and renderer in ["video", "manim"]:
                quality = "❌ NONE"
            elif renderer == "video" and short_prompts > 0:
                 quality = f"⚠️ {short_prompts} Short"

            outfile.write(f"{sid:<4} {stype:<10} {renderer:<8} {num_segments:<5} {num_prompts:<5} {placeholders:<12} {quality}\n")

            if sid == 12:
                outfile.write("\n--- SECTION 12 PROMPT DUMP (First 3) ---\n")
                for i, p in enumerate(prompts[:3]):
                    outfile.write(f"{i+1}. {p[:100]}...\n")

        outfile.write("-" * 80 + "\n")
        outfile.write(f"Total Placeholders: {total_placeholders}\n")

if __name__ == "__main__":
    analyze_prompts()
