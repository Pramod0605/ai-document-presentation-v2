import json
from pathlib import Path

p = json.load(open('player/jobs/d76a0cc1/presentation.json', encoding='utf-8'))
sec2 = [s for s in p['sections'] if s['section_id'] == 2][0]
segs = sec2['narration']['segments']

print(f'Section 2 has {len(segs)} segments')

seg0 = segs[0]
text = seg0.get('text', '')
print(f'Segment 0 text type: {type(text)}')
print(f'Segment 0 text length: {len(str(text))}')
print(f'Segment 0 text preview: {str(text)[:150]}')

print('\nChecking if text is being stripped or modified:')
print(f'Text has content: {bool(text)}')
print(f'Text stripped has content: {bool(str(text).strip())}')
