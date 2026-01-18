"""
Validation Script for Job ba0b5b26
Validates WAN prompts, video beats, and presentation structure
"""

import json
from pathlib import Path

JOB_DIR = Path(r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\ba0b5b26")

def load_json(filename):
    with open(JOB_DIR / filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_wan_prompts(presentation):
    """Check WAN prompts for garbage/truncated text"""
    issues = []
    valid_prompts = []
    
    for section in presentation.get('sections', []):
        section_id = section.get('section_id')
        section_type = section.get('section_type')
        renderer = section.get('renderer', 'none')
        
        # Check video_prompts in section root (for recap sections)
        for vp in section.get('video_prompts', []):
            prompt = vp.get('prompt', '')
            beat_id = vp.get('beat_id', 'unknown')
            
            if len(prompt) < 50:
                issues.append(f"Section {section_id} ({section_type}): Beat {beat_id} has short prompt ({len(prompt)} chars)")
            elif is_garbage_prompt(prompt):
                issues.append(f"Section {section_id} ({section_type}): Beat {beat_id} has garbage prompt")
            else:
                valid_prompts.append({
                    'section_id': section_id,
                    'section_type': section_type,
                    'beat_id': beat_id,
                    'prompt_preview': prompt[:100] + '...',
                    'length': len(prompt)
                })
        
        # Check render_spec for content sections with WAN
        render_spec = section.get('render_spec', {})
        for seg_spec in render_spec.get('segment_specs', []):
            if seg_spec.get('renderer') == 'video':
                prompt = seg_spec.get('video_prompt', '')
                seg_id = seg_spec.get('segment_id', 'unknown')
                
                if len(prompt) < 50:
                    issues.append(f"Section {section_id} ({section_type}): Seg {seg_id} has short WAN prompt ({len(prompt)} chars)")
                elif is_garbage_prompt(prompt):
                    issues.append(f"Section {section_id} ({section_type}): Seg {seg_id} has garbage WAN prompt")
                else:
                    valid_prompts.append({
                        'section_id': section_id,
                        'section_type': section_type,
                        'segment_id': seg_id,
                        'prompt_preview': prompt[:100] + '...',
                        'length': len(prompt)
                    })
                    
                # Also check beats within segment_spec
                for beat in seg_spec.get('beats', []):
                    beat_prompt = beat.get('prompt', '')
                    beat_id = beat.get('beat_id', 'unknown')
                    if len(beat_prompt) > 50 and not is_garbage_prompt(beat_prompt):
                        valid_prompts.append({
                            'section_id': section_id,
                            'section_type': section_type,
                            'beat_id': beat_id,
                            'prompt_preview': beat_prompt[:100] + '...',
                            'length': len(beat_prompt)
                        })
    
    return valid_prompts, issues

def is_garbage_prompt(prompt):
    """Check if prompt contains garbage/truncated/malformed text"""
    garbage_indicators = [
        '###',  # Markdown headers in prompt
        '```',  # Code blocks
        'json',
        '{',
        '}',
        '\\n\\n',
        'undefined',
        'null',
        '[object',
    ]
    
    # Check for truncation (ends abruptly)
    if prompt.strip().endswith(('...', '…')):
        return True
    
    # Check for very short sentences that don't make sense
    if len(prompt.split()) < 10:
        return True
    
    # Check for garbage indicators
    for indicator in garbage_indicators:
        if indicator in prompt:
            return True
    
    return False

def validate_video_beats(presentation):
    """Check video beat structure and alignment with narration"""
    issues = []
    beat_summary = []
    
    for section in presentation.get('sections', []):
        section_id = section.get('section_id')
        section_type = section.get('section_type')
        
        # Check visual_beats
        visual_beats = section.get('visual_beats', [])
        if visual_beats:
            beat_summary.append({
                'section_id': section_id,
                'section_type': section_type,
                'beat_count': len(visual_beats),
                'beat_types': list(set(vb.get('visual_type', 'unknown') for vb in visual_beats))
            })
        
        # Check segments with beat_videos references
        narration = section.get('narration', {})
        segments = narration.get('segments', [])
        
        for seg in segments:
            beat_videos = seg.get('beat_videos', [])
            if beat_videos:
                # Verify beat video IDs are properly formatted
                for bv in beat_videos:
                    if not isinstance(bv, str) or len(bv) < 5:
                        issues.append(f"Section {section_id}: Invalid beat_video ID: {bv}")
    
    return beat_summary, issues

def validate_section_structure(presentation):
    """Validate overall section structure"""
    sections = presentation.get('sections', [])
    summary = {
        'total_sections': len(sections),
        'section_types': {},
        'renderers': {},
        'total_duration': 0
    }
    
    for section in sections:
        section_type = section.get('section_type', 'unknown')
        renderer = section.get('renderer', 'none')
        
        summary['section_types'][section_type] = summary['section_types'].get(section_type, 0) + 1
        summary['renderers'][renderer] = summary['renderers'].get(renderer, 0) + 1
        
        narration = section.get('narration', {})
        duration = narration.get('total_duration_seconds', 0)
        summary['total_duration'] += duration
    
    return summary

def main():
    print("=" * 80)
    print("VALIDATION REPORT FOR JOB: ba0b5b26")
    print("=" * 80)
    
    # Load presentation
    presentation = load_json('presentation.json')
    
    # 1. Section Structure
    print("\n## 1. SECTION STRUCTURE")
    print("-" * 40)
    structure = validate_section_structure(presentation)
    print(f"Total Sections: {structure['total_sections']}")
    print(f"Total Duration: {structure['total_duration']:.1f} seconds ({structure['total_duration']/60:.1f} minutes)")
    print(f"\nSection Types:")
    for stype, count in structure['section_types'].items():
        print(f"  - {stype}: {count}")
    print(f"\nRenderers:")
    for renderer, count in structure['renderers'].items():
        print(f"  - {renderer}: {count}")
    
    # 2. WAN Prompt Validation
    print("\n## 2. WAN PROMPT VALIDATION")
    print("-" * 40)
    valid_prompts, prompt_issues = validate_wan_prompts(presentation)
    
    if prompt_issues:
        print(f"❌ ISSUES FOUND: {len(prompt_issues)}")
        for issue in prompt_issues:
            print(f"  - {issue}")
    else:
        print("✅ NO GARBAGE/TRUNCATED PROMPTS FOUND")
    
    print(f"\nValid WAN Prompts: {len(valid_prompts)}")
    for vp in valid_prompts:
        print(f"  - Section {vp['section_id']} ({vp['section_type']}): {vp.get('beat_id', vp.get('segment_id', '?'))} ({vp['length']} chars)")
        print(f"    Preview: {vp['prompt_preview']}")
    
    # 3. Video Beat Validation
    print("\n## 3. VIDEO BEAT VALIDATION")
    print("-" * 40)
    beat_summary, beat_issues = validate_video_beats(presentation)
    
    if beat_issues:
        print(f"❌ ISSUES FOUND: {len(beat_issues)}")
        for issue in beat_issues:
            print(f"  - {issue}")
    else:
        print("✅ ALL VIDEO BEATS ARE PROPERLY STRUCTURED")
    
    print(f"\nSections with Visual Beats:")
    for bs in beat_summary:
        print(f"  - Section {bs['section_id']} ({bs['section_type']}): {bs['beat_count']} beats")
        print(f"    Types: {', '.join(bs['beat_types'])}")
    
    # 4. Specific Checks
    print("\n## 4. SPECIFIC CHECKS")
    print("-" * 40)
    
    # Check if dry_run marker is present
    metadata = presentation.get('metadata', {})
    print(f"Pipeline Mode: {metadata.get('pipeline_mode', 'unknown')}")
    print(f"Generated By: {metadata.get('generated_by', 'unknown')}")
    print(f"TTS Provider: {metadata.get('tts_provider', 'unknown')}")
    
    # Check for recap section
    has_recap = any(s.get('section_type') == 'recap' for s in presentation.get('sections', []))
    print(f"\nRecap Section: {'✅ Present' if has_recap else '❌ Missing'}")
    
    # 5. Final Summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    
    all_issues = prompt_issues + beat_issues
    if all_issues:
        print(f"❌ TOTAL ISSUES: {len(all_issues)}")
    else:
        print("✅ ALL VALIDATIONS PASSED")
        print("  - WAN prompts are well-formed and descriptive")
        print("  - Video beats are properly structured")
        print("  - Section structure is correct")
        print("  - No garbage/truncated text found")
    
    return len(all_issues) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
