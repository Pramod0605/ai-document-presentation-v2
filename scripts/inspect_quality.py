import json
from pathlib import Path

JOB_ID = "dd435125"
JOB_DIR = Path(f"player/jobs/{JOB_ID}")

def inspect_quality():
    print(f"=== QUALITY INSPECTION: {JOB_ID} ===")
    
    try:
        with open(JOB_DIR / "presentation.json", "r", encoding="utf-8") as f:
            pres = json.load(f)
    except Exception as e:
        print(f"Error: {e}")
        return

    sections = pres.get("sections", [])
    
    # 1. Global Sections check
    types = [s.get("section_type") for s in sections]
    print(f"\n[STRUCTURE AUDIT]")
    print(f"Total Sections: {len(sections)}")
    print(f"Intro:   {'✅' if 'intro' in types else '❌'}")
    print(f"Summary: {'✅' if 'summary' in types else '❌'}")
    print(f"Quiz:    {'✅' if 'quiz' in types else '❌'}")
    print(f"Memory:  {'✅' if 'memory' in types else '❌'}")
    print(f"Recap:   {'✅' if 'recap' in types else '❌'}")

    # 2. Quiz & Memory Logic
    print(f"\n[INTERACTIVE LOGIC]")
    if 'quiz' in types:
        quiz = next(s for s in sections if s['section_type'] == 'quiz')
        qs = quiz.get("questions", [])
        valid_explanations = sum(1 for q in qs if q.get("explanation") and len(q.get("explanation")) > 10)
        print(f"Quiz Questions: {len(qs)}")
        print(f"Valid Explanations (Narrator Ready): {valid_explanations}/{len(qs)}")
    else:
        print("Quiz: Not Found")

    if 'recap' in types:
        recap = next(s for s in sections if s['section_type'] == 'recap')
        prompts = recap.get("video_prompts", [])
        print(f"Recap Video Prompts: {len(prompts)} (Target: 5)")
        print(f"Recap Valid Length (>80 words): {sum(1 for p in prompts if len(p.split()) > 70)}")

    # 3. Content & Renderers
    print(f"\n[CONTENT INTELLIGENCE]")
    manim_specs = 0
    video_prompts = 0
    
    for s in sections:
        if s.get("derived_renderer") == "manim":
             spec = s.get("manim_spec", "")
             if spec and len(spec.split()) > 50: manim_specs += 1
        if s.get("derived_renderer") == "video":
             prompts = s.get("video_prompts", [])
             video_prompts += sum(1 for p in prompts if len(p.split()) > 50)

    print(f"Manim Animations (Complex Math): {manim_specs}")
    print(f"Video Scenes (Bio/History): {video_prompts}")


    # 3. Visual Beats Analysis (Teach & Show)
    print(f"\n[TEACH & SHOW FIDELITY]")
    equations = 0
    images = 0
    total_beats = 0
    
    for s in sections:
        beats = s.get("visual_beats", [])
        total_beats += len(beats)
        for b in beats:
            if b.get("visual_type") == "equation": equations += 1
            if b.get("visual_type") == "image": images += 1
            
    print(f"Total Visual Beats: {total_beats}")
    print(f"LaTeX Equations: {equations}")
    print(f"Images Injected: {images}")
    
    # 4. Sync Check (Narration vs Visuals)
    print(f"\n[SYNC CHECK SAMPLE]")
    # Grab one random content section
    content_secs = [s for s in sections if s.get("section_type") == "content"]
    if content_secs:
        sample = content_secs[0]
        narr_segs = len(sample.get("narration", {}).get("segments", []))
        vis_beats = len(sample.get("visual_beats", []))
        print(f"Sample Section: '{sample.get('title')}'")
        print(f"  Narration Segments: {narr_segs}")
        print(f"  Visual Beats: {vis_beats}")
        if abs(narr_segs - vis_beats) <= 1:
            print("  ✅ Sync Status: TIGHT (Beats align with segments)")
        else:
            print("  ⚠️ Sync Status: LOOSE (Count mismatch, might be intentional)")

if __name__ == "__main__":
    inspect_quality()
