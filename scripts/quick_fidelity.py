import json
from pathlib import Path

JOB_ID = "6b12114f"
BASE_DIR = Path(f"player/jobs/{JOB_ID}")
JSON_PATH = BASE_DIR / "presentation.json"
MD_PATH = BASE_DIR / "source_markdown.md"

print("=" * 70)
print(f"CONTENT FIDELITY ANALYSIS: Job {JOB_ID}")
print("=" * 70)

# Load files
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

with open(MD_PATH, 'r', encoding='utf-8') as f:
    md_content = f.read()

# Basic stats
generator = data.get('metadata', {}).get('generated_by', 'unknown')
sections = data.get('sections', [])

print(f"\n[1] PIPELINE")
print(f"   Generator: {generator}")
print(f"   Mode: {'V2.5 Director' if 'director' in generator else 'Legacy'}")

print(f"\n[2] SOURCE MARKDOWN")
print(f"   Total Characters: {len(md_content)}")
print(f"   Total Lines: {len(md_content.split(chr(10)))}")
headings = [l for l in md_content.split('\n') if l.strip().startswith('#')]
print(f"   Headings: {len(headings)}")
table_lines = [l for l in md_content.split('\n') if '|' in l and l.strip()]
print(f"   Table Lines: {len(table_lines)}")

print(f"\n[3] PRESENTATION JSON")
print(f"   Sections: {len(sections)}")

total_segments = 0
total_pointers = 0
total_narration_chars = 0

for sec in sections:
    narration = sec.get('narration', {})
    segments = narration.get('segments', [])
    total_segments += len(segments)
    
    for seg in segments:
        text = seg.get('text', '')
        total_narration_chars += len(text)
        
        vis = seg.get('visual_content', {})
        pointer = vis.get('markdown_pointer')
        if pointer:
            total_pointers += 1

print(f"   Total Segments: {total_segments}")
print(f"   Segments with Pointers: {total_pointers}")
print(f"   Narration Characters: {total_narration_chars}")

print(f"\n[4] FIDELITY METRICS")
pointer_coverage = (total_pointers / total_segments * 100) if total_segments > 0 else 0
print(f"   Pointer Coverage: {pointer_coverage:.1f}% ({total_pointers}/{total_segments} segments)")

print(f"\n[5] VERDICT")
if pointer_coverage >= 70 and total_pointers > 0:
    print(f"   ✅ HIGH FIDELITY - V2.5 Director Mode working correctly")
elif pointer_coverage >=  40:
    print(f"   ⚠️  MEDIUM FIDELITY - Some segments missing pointers")
else:
    print(f"   ❌ LOW FIDELITY - Most content not using pointers")

print("\n" + "=" * 70)
