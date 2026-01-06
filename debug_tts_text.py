"""
Debug Script: Check exactly what text TTS is receiving
"""
import json
from pathlib import Path

JOB_ID = "d76a0cc1"
pres_path = Path(f"player/jobs/{JOB_ID}/presentation.json")

with open(pres_path, "r", encoding="utf-8") as f:
    presentation = json.load(f)

print("=" * 80)
print("TTS NARRATION DEBUG FOR JOB", JOB_ID)
print("=" * 80)

sections = presentation.get("sections", [])
print(f"\nTotal sections: {len(sections)}")

for sec_idx, section in enumerate(sections):
    section_id = section.get("section_id", f"section_{sec_idx}")
    title = section.get("title", "Untitled")
    
    print(f"\n{'='*80}")
    print(f"Section {section_id}: {title}")
    print(f"{'='*80}")
    
    # Check narration structure
    narration = section.get("narration")
    print(f"Has 'narration' key: {narration is not None}")
    print(f"Type of narration: {type(narration)}")
    
    if narration is None:
        print("  ❌ PROBLEM: No narration dict found!")
        continue
    
    if isinstance(narration, dict):
        print(f"  Narration dict keys: {list(narration.keys())}")
        segments = narration.get("segments")
        print(f"  Has 'segments' key: {segments is not None}")
        print(f"  Type of segments: {type(segments)}")
        
        if segments is None:
            print("  ❌ PROBLEM: No segments found in narration!")
            continue
            
        if isinstance(segments, list):
            print(f"  Number of segments: {len(segments)}")
            
            for seg_idx, segment in enumerate(segments):
                seg_id = segment.get("segment_id", f"seg_{seg_idx}")
                text = segment.get("text", "")
                
                print(f"\n  Segment {seg_idx} (ID: {seg_id}):")
                print(f"    Segment type: {type(segment)}")
                print(f"    Segment keys: {list(segment.keys()) if isinstance(segment, dict) else 'NOT A DICT'}")
                print(f"    Has 'text' key: {'text' in segment if isinstance(segment, dict) else False}")
                print(f"    Text value type: {type(text)}")
                print(f"    Text length: {len(str(text))}")
                print(f"    Text (first 100 chars): '{str(text)[:100]}'")
                
                if not str(text).strip():
                    print(f"    ❌ PROBLEM: Text is empty or whitespace!")
                else:
                    # This is what TTS will create as filename
                    audio_filename = f"{section_id}_{seg_id}"
                    print(f"    Audio file would be: {audio_filename}.mp3")
                    print(f"    ✅ Text looks OK")
        else:
            print(f"  ❌ PROBLEM: segments is not a list! Type: {type(segments)}")
    else:
        print(f"  ❌ PROBLEM: narration is not a dict! Type: {type(narration)}")

print(f"\n{'='*80}")
print("DEBUG COMPLETE")
print(f"{'='*80}")
