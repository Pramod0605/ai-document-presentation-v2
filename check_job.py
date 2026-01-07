"""Quick job content checker"""
import json
from pathlib import Path

JOB_ID = "4ee21a06"
JOB_DIR = Path(f"player/jobs/{JOB_ID}")

# Load presentation
with open(JOB_DIR / "presentation.json", 'r', encoding='utf-8') as f:
    p = json.load(f)

# Load markdown
with open(JOB_DIR / "source_markdown.md", 'r', encoding='utf-8') as f:
    md = f.read()

print("="*60)
print(f"JOB {JOB_ID} CONTENT CHECK")
print("="*60)

print(f"\nPresentation.json: {(JOB_DIR / 'presentation.json').stat().st_size:,} bytes")
print(f"Source Markdown: {len(md):,} chars")

sections = p.get('sections', [])
print(f"\nTotal Sections: {len(sections)}")

meta = p.get('metadata', {})
print(f"Title: {meta.get('title', 'N/A')}")
print(f"Pipeline: {meta.get('pipeline_mode', 'N/A')}")

print("\nSections Summary:")
total_segs = 0
for i, s in enumerate(sections):
    title = s.get('title', '?')[:35]
    segs = s.get('narration', {}).get('segments', [])
    renderer = s.get('visual', {}).get('renderer', 'none')
    total_segs += len(segs)
    print(f"  {i+1:2}. [{renderer:6}] {title}... ({len(segs)} segs)")

print(f"\nTotal Narration Segments: {total_segs}")

# Check audio folder
audio_dir = JOB_DIR / "audio"
if audio_dir.exists():
    audio_files = list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.wav"))
    non_empty = [f for f in audio_files if f.stat().st_size > 1000]
    print(f"\nAudio files: {len(audio_files)} total, {len(non_empty)} with content")
else:
    print("\nNo audio folder yet")

print("="*60)
