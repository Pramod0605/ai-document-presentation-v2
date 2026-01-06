
import json
 
import os
import sys

# Define path to job
job_id = "e815947d"
presentation_path = f"player/jobs/{job_id}/presentation.json"

if not os.path.exists(presentation_path):
    print(f"❌ Error: Presentation {presentation_path} not found.")
    sys.exit(1)

print(f"🔍 Analyzing Job {job_id} Artifacts...\n")

with open(presentation_path, "r", encoding="utf-8") as f:
    data = json.load(f)

sections = data.get("sections", [])
print(f"✅ Total Sections Generated: {len(sections)}")

# Track mandatory types
found_types = set()
quiz_count = 0
memory_count = 0
visual_beats_count = 0

print("\n--- SECTION BREAKDOWN ---")
for i, section in enumerate(sections):
    stype = section.get("section_type", "unknown")
    sid = section.get("section_id", f"s{i}")
    found_types.add(stype)
    
    # Check Narration
    narration_len = len(section.get("narration", {}).get("full_text", ""))
    segments_count = len(section.get("narration", {}).get("segments", []))
    
    # Check Visuals
    v_beats = len(section.get("visual_beats", []))
    visual_beats_count += v_beats
    
    info = f"[{i+1}] {stype.upper()} ({sid}): {segments_count} segments, {v_beats} visual beats."

    if stype == "quiz":
        q_data = section.get("quiz_data", {}).get("questions", [])
        info += f" -> found {len(q_data)} questions."
        if len(q_data) > 0: quiz_count += 1
    
    if stype == "memory":
        cards = section.get("flashcards", [])
        info += f" -> found {len(cards)} cards."
        if len(cards) > 0: 
            memory_count += 1
            print(f"\n   [MEMORY CONTENT]")
            for c in cards:
                print(f"   - {c.get('front', 'Unknown')}: {c.get('back', 'Unknown')}")
        
    if stype == "recap":
        v_prompts = section.get("video_prompts", [])
        info += f" -> found {len(v_prompts)} video prompts."

    print(info)

print("\n--- FINAL VERDICT ---")
print(f"Summary Found: {'✅' if 'summary' in found_types else '❌'}")
print(f"Quiz Found: {'✅' if 'quiz' in found_types else '❌'} ({quiz_count} sections)")
print(f"Memory Found: {'✅' if 'memory' in found_types else '❌'} ({memory_count} sections)")
print(f"Recap Found: {'✅' if 'recap' in found_types else '❌'}")
print(f"Content Found: {'✅' if 'content' in found_types else '❌'}")

if 'intro' in found_types and 'recap' in found_types and 'content' in found_types:
    print("\n🌟 RESULT: COMPLETE V2.5 STRUCTURE VERIFIED")
else:
    print("\n⚠️ RESULT: INCOMPLETE STRUCTURE")
