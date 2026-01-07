"""
Deep analysis of job to understand what's missing vs Director Bible
"""
import json
from pathlib import Path

JOB_ID = "4ee21a06"
job_dir = Path(f"player/jobs/{JOB_ID}")
p = json.load(open(job_dir / "presentation.json", 'r', encoding='utf-8'))

print("=" * 70)
print(f"DETAILED ANALYSIS: JOB {JOB_ID}")
print("=" * 70)

# Check for video_prompts in any section
print("\n📹 SECTIONS WITH VIDEO_PROMPTS (for WAN/Kie.ai):")
video_prompt_sections = []
for i, s in enumerate(p.get('sections', [])):
    vp = s.get('visual', {}).get('video_prompts', [])
    if vp:
        video_prompt_sections.append((i+1, s.get('title','?')[:30], len(vp)))

if video_prompt_sections:
    for idx, title, count in video_prompt_sections:
        print(f"  S{idx}: {title} ({count} prompts)")
else:
    print("  NONE FOUND! ❌")

# Check Memory section
print("\n🧠 MEMORY SECTION CHECK (should have 5 flashcards):")
memory_found = False
for i, s in enumerate(p.get('sections', [])):
    title = s.get('title', '').lower()
    if 'memory' in title or 'flashcard' in title or 'key concept' in title:
        memory_found = True
        segs = s.get('narration', {}).get('segments', [])
        print(f"  S{i+1}: {s.get('title','?')[:40]}")
        print(f"  Segments: {len(segs)} (Director Bible requires 5)")
        for j, seg in enumerate(segs[:3]):
            text = seg.get('text', '')[:60]
            print(f"    {j+1}. {text}...")
if not memory_found:
    print("  NONE FOUND! ❌")

# Check Recap section  
print("\n🎬 RECAP SECTION CHECK (should have 5 segments + 5 video prompts):")
recap_found = False
for i, s in enumerate(p.get('sections', [])):
    title = s.get('title', '').lower()
    if 'recap' in title or 'conclusion' in title or 'closing' in title:
        recap_found = True
        segs = s.get('narration', {}).get('segments', [])
        vp = s.get('visual', {}).get('video_prompts', [])
        print(f"  S{i+1}: {s.get('title','?')[:40]}")
        print(f"  Narration Segments: {len(segs)} (should be 5)")
        print(f"  Video Prompts: {len(vp)} (should be 5)")
        if vp:
            print(f"  First prompt: {vp[0][:80]}...")
if not recap_found:
    print("  NONE FOUND! ❌")

# Check last 5 sections
print("\n📋 LAST 5 SECTIONS (to see structure):")
for s in p.get('sections', [])[-5:]:
    title = s.get('title', '?')[:40]
    segs = len(s.get('narration', {}).get('segments', []))
    renderer = s.get('visual', {}).get('renderer', 'none')
    print(f"  [{renderer:10}] {title}... ({segs} segs)")

# Check Content sections for video prompts
print("\n📖 CONTENT SECTIONS WITH WAN VIDEO NEEDS:")
content_needs_video = 0
for i, s in enumerate(p.get('sections', [])):
    title = s.get('title', '').lower()
    renderer = s.get('visual', {}).get('renderer', 'none')
    # Biology content should have wan_video renderer
    if 'content' not in title and 'quiz' not in title and 'question' not in title:
        continue
    if renderer == 'none':
        content_needs_video += 1

print(f"  Content sections with renderer='none': {content_needs_video}")
print(f"  (For Biology, these should typically have 'wan_video' renderer)")

print("\n" + "=" * 70)
