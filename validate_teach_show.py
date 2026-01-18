"""
Validates Teach→Show pattern and WAN beat linking for job ba0b5b26
"""
import json
from pathlib import Path

job_dir = Path(r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\ba0b5b26")
pres = json.load(open(job_dir / "presentation.json", encoding="utf-8"))

print("=" * 70)
print("TEACH → SHOW VALIDATION FOR JOB ba0b5b26")
print("=" * 70)

for section in pres.get("sections", []):
    section_id = section.get("section_id")
    section_type = section.get("section_type")
    renderer = section.get("renderer", "none")
    
    # Only check content sections with video renderer
    if section_type != "content" or renderer != "video":
        continue
    
    print(f"\n## Section {section_id}: {section.get('title', '')[:50]}")
    print(f"   Renderer: {renderer}")
    print("-" * 60)
    
    narration = section.get("narration", {})
    segments = narration.get("segments", [])
    
    # Get video_prompts from section
    video_prompts = section.get("video_prompts", [])
    prompt_map = {vp["beat_id"]: vp for vp in video_prompts}
    
    # Also check render_spec
    render_spec = section.get("render_spec", {})
    segment_specs = render_spec.get("segment_specs", [])
    spec_map = {ss["segment_id"]: ss for ss in segment_specs}
    
    show_count = 0
    show_with_beats = 0
    
    for seg in segments:
        seg_id = seg.get("segment_id", "?")
        purpose = seg.get("purpose", "?")
        directives = seg.get("display_directives", {})
        visual_layer = directives.get("visual_layer", "hide")
        beat_videos = seg.get("beat_videos", [])
        
        is_show = visual_layer == "show"
        
        if is_show:
            show_count += 1
            has_beats = len(beat_videos) > 0
            
            # Check if beats have prompts
            prompts_found = []
            for beat_id in beat_videos:
                if beat_id in prompt_map:
                    prompt = prompt_map[beat_id].get("prompt", "")[:80]
                    prompts_found.append(f"{beat_id}: {prompt}...")
            
            # Also check segment_specs
            seg_spec = spec_map.get(seg_id, {})
            seg_prompt = seg_spec.get("video_prompt", "")
            beats_in_spec = seg_spec.get("beats", [])
            
            if has_beats or seg_prompt or beats_in_spec:
                show_with_beats += 1
                status = "✅"
            else:
                status = "❌ MISSING WAN PROMPT"
            
            print(f"\n  {seg_id} (SHOW) {status}")
            print(f"    visual_layer: {visual_layer}")
            print(f"    beat_videos: {beat_videos}")
            
            if prompts_found:
                for p in prompts_found:
                    print(f"    ✓ Prompt: {p}")
            
            if seg_prompt:
                print(f"    ✓ Segment video_prompt: {seg_prompt[:80]}...")
            
            if beats_in_spec:
                for b in beats_in_spec:
                    print(f"    ✓ Beat spec: {b.get('beat_id')} ({b.get('duration')}s)")
        else:
            print(f"\n  {seg_id} (TEACH) - visual_layer: {visual_layer}")
    
    print(f"\n  Summary: {show_with_beats}/{show_count} SHOW segments have WAN prompts")

# Also check recap section
print("\n" + "=" * 70)
print("RECAP SECTION (WAN Videos)")
print("=" * 70)

for section in pres.get("sections", []):
    if section.get("section_type") != "recap":
        continue
    
    print(f"\n## Section {section.get('section_id')}: Recap")
    
    video_prompts = section.get("video_prompts", [])
    segments = section.get("narration", {}).get("segments", [])
    
    for seg in segments:
        beat_videos = seg.get("beat_videos", [])
        seg_text = seg.get("text", "")[:50]
        
        for beat_id in beat_videos:
            prompt_found = next((vp for vp in video_prompts if vp.get("beat_id") == beat_id), None)
            if prompt_found:
                print(f"  ✅ {beat_id}: {prompt_found.get('prompt', '')[:60]}...")
            else:
                print(f"  ❌ {beat_id}: NO PROMPT FOUND")

print("\n" + "=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)
