"""
Player Beat Video Sync Verification Script
Usage: python verify_player_sync.py <job_id>

Verifies that beat videos are correctly mapped to their segment times.
"""

import json
import os
import sys


def verify_beat_sync(job_id):
    """Verify beat videos are correctly mapped to segment times."""
    job_path = f"player/jobs/{job_id}/presentation.json"
    
    if not os.path.exists(job_path):
        print(f"❌ Job not found: {job_path}")
        return False
    
    with open(job_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    errors = []
    total_sections = 0
    total_beats = 0
    
    print(f"=" * 60)
    print(f"Beat Video Sync Verification - Job: {job_id}")
    print(f"=" * 60)
    
    for section in data.get('sections', []):
        section_id = section.get('section_id')
        section_type = section.get('section_type', 'unknown')
        renderer = section.get('renderer', 'none')
        
        # Only check sections that should have videos
        if renderer not in ('manim', 'video'):
            continue
            
        total_sections += 1
        segments = section.get('narration', {}).get('segments', [])
        
        print(f"\n{'─' * 60}")
        print(f"Section {section_id}: {section.get('title', 'Untitled')}")
        print(f"Type: {section_type} | Renderer: {renderer}")
        print(f"{'─' * 60}")
        
        cumulative_time = 0
        beat_index = 0
        
        for seg_idx, seg in enumerate(segments):
            duration = seg.get('duration_seconds', 5)
            seg_start = cumulative_time
            seg_end = cumulative_time + duration
            
            directives = seg.get('display_directives', {})
            text_layer = directives.get('text_layer', 'show')
            visual_layer = directives.get('visual_layer', 'hide')
            
            beat_videos = seg.get('beat_videos', [])
            phase = "SHOW" if visual_layer == 'show' else "TEACH"
            
            if beat_videos:
                expected_file = f"topic_{section_id}_beat_{beat_index}.mp4"
                video_path = f"player/jobs/{job_id}/videos/{expected_file}"
                file_exists = os.path.exists(video_path)
                
                status = "✅" if file_exists else "❌ MISSING"
                print(f"  Seg {seg_idx} [{phase:5}] {seg_start:6.1f}s - {seg_end:6.1f}s | Beat {beat_index} | {status}")
                
                if not file_exists:
                    errors.append(f"Section {section_id} Seg {seg_idx}: Missing {expected_file}")
                
                total_beats += 1
                beat_index += 1
            else:
                print(f"  Seg {seg_idx} [{phase:5}] {seg_start:6.1f}s - {seg_end:6.1f}s | (no video)")
            
            cumulative_time += duration
        
        print(f"  Total duration: {cumulative_time:.1f}s | Beat videos: {beat_index}")
    
    print(f"\n{'=' * 60}")
    print(f"Summary: {total_sections} sections, {total_beats} beat videos")
    
    if errors:
        print(f"\n❌ ERRORS FOUND ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print(f"\n✅ All beat videos correctly mapped!")
        return True


if __name__ == "__main__":
    job_id = sys.argv[1] if len(sys.argv) > 1 else "ca1d5e9c"
    success = verify_beat_sync(job_id)
    sys.exit(0 if success else 1)
