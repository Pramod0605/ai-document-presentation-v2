import json
import re
from pathlib import Path
from collections import defaultdict

JOB_ID = "6b12114f"
BASE_DIR = Path(f"player/jobs/{JOB_ID}")
JSON_PATH = BASE_DIR / "presentation.json"
MD_PATH = BASE_DIR / "source_markdown.md"

def extract_markdown_elements(md_content):
    """Extract all meaningful content from markdown"""
    elements = {
        'headings': [],
        'tables': [],
        'images': [],
        'equations': [],
        'lists': [],
        'paragraphs': [],
        'code_blocks': []
    }
    
    lines = md_content.split('\n')
    in_table = False
    in_code = False
    current_paragraph = []
    
    for line in lines:
        # Headings
        if line.strip().startswith('#'):
            elements['headings'].append(line.strip())
        
        # Tables
        elif '|' in line and not in_code:
            elements['tables'].append(line.strip())
            in_table = True
        elif in_table and not '|' in line:
            in_table = False
        
        # Images
        elif line.strip().startswith('!['):
            elements['images'].append(line.strip())
        
        # Equations (LaTeX)
        elif '$$' in line or '$' in line:
            elements['equations'].append(line.strip())
        
        # Lists
        elif re.match(r'^\s*[-*\d]+\.?\s', line):
            elements['lists'].append(line.strip())
        
        # Code blocks
        elif line.strip().startswith('```'):
            in_code = not in_code
            if not in_code:
                elements['code_blocks'].append('```')
        elif in_code:
            elements['code_blocks'].append(line)
        
        # Regular paragraphs
        elif line.strip() and not in_table and not in_code:
            current_paragraph.append(line.strip())
    
    if current_paragraph:
        elements['paragraphs'].extend(current_paragraph)
    
    return elements

def extract_json_content(json_data):
    """Extract all text content from presentation JSON"""
    content = {
        'narration_text': [],
        'visual_text': [],
        'pointers': [],
        'video_prompts': [],
        'manim_prompts': []
    }
    
    sections = json_data.get('sections', [])
    for sec in sections:
        # Narration text
        narration = sec.get('narration', {})
        segments = narration.get('segments', [])
        
        for seg in segments:
            # Narration
            text = seg.get('text', '')
            if text:
                content['narration_text'].append(text)
            
            # Visual content
            vis = seg.get('visual_content', {})
            
            # Pointers
            pointer = vis.get('markdown_pointer')
            if pointer:
                content['pointers'].append({
                    'start': pointer.get('start_phrase', ''),
                    'end': pointer.get('end_phrase', '')
                })
            
            # Video prompts
            video_prompt = vis.get('video_prompt')
            if video_prompt:
                content['video_prompts'].append(video_prompt)
            
            # Manim
            manim_spec = vis.get('manim_spec')
            if manim_spec:
                content['manim_prompts'].append(manim_spec)
    
    return content

def analyze_coverage(md_elements, json_content, md_text):
    """Analyze what's covered and what's missing"""
    report = {
        'headings_covered': 0,
        'headings_missing': [],
        'tables_found': len(md_elements['tables']),
        'tables_referenced': 0,
        'images_found': len(md_elements['images']),
        'images_referenced': 0,
        'equations_found': len(md_elements['equations']),
        'equations_referenced': 0,
        'text_coverage_pct': 0,
        'pointer_count': len(json_content['pointers']),
        'missing_sections': []
    }
    
    # Check headings
    for heading in md_elements['headings']:
        heading_text = heading.lstrip('#').strip()
        found = False
        for narr in json_content['narration_text']:
            if heading_text.lower() in narr.lower():
                found = True
                break
        
        if found:
            report['headings_covered'] += 1
        else:
            report['headings_missing'].append(heading_text)
    
    # Check table references
    for table_line in md_elements['tables']:
        for narr in json_content['narration_text']:
            if 'table' in narr.lower():
                report['tables_referenced'] += 1
                break
    
    # Check image references
    for img in md_elements['images']:
        for prompt in json_content['video_prompts']:
            if 'diagram' in prompt.lower() or 'figure' in prompt.lower():
                report['images_referenced'] += 1
                break
    
    # Check equation coverage
    for eq in md_elements['equations']:
        for narr in json_content['narration_text']:
            if any(char in narr for char in ['=', '+', '-', '×', '÷']):
                report['equations_referenced'] += 1
                break
    
    # Estimate text coverage via pointers
    covered_chars = 0
    for ptr in json_content['pointers']:
        start_idx = md_text.find(ptr['start'])
        end_idx = md_text.find(ptr['end'])
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            covered_chars += (end_idx - start_idx)
    
    total_chars = len(md_text.strip())
    if total_chars > 0:
        report['text_coverage_pct'] = round((covered_chars / total_chars) * 100, 1)
    
    return report

def generate_analysis():
    print(f"=" * 70)
    print(f"   CONTENT FIDELITY ANALYSIS: Job {JOB_ID}")
    print(f"=" * 70)
    
    if not JSON_PATH.exists():
        print("❌ presentation.json NOT FOUND")
        return
    
    if not MD_PATH.exists():
        print("❌ source_markdown.md NOT FOUND")
        return
    
    # Load files
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    with open(MD_PATH, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    print(f"\n[1] SOURCE MARKDOWN ANALYSIS")
    md_elements = extract_markdown_elements(md_content)
    print(f"   • Headings: {len(md_elements['headings'])}")
    print(f"   • Tables: {len(md_elements['tables'])} rows")
    print(f"   • Images: {len(md_elements['images'])}")
    print(f"   • Equations: {len(md_elements['equations'])}")
    print(f"   • Lists: {len(md_elements['lists'])} items")
    print(f"   • Paragraphs: {len(md_elements['paragraphs'])} lines")
    print(f"   • Total Characters: {len(md_content)}")
    
    print(f"\n[2] PRESENTATION JSON ANALYSIS")
    json_content = extract_json_content(json_data)
    print(f"   • Sections: {len(json_data.get('sections', []))}")
    print(f"   • Narration Segments: {len(json_content['narration_text'])}")
    print(f"   • Pointers: {len(json_content['pointers'])}")
    print(f"   • Video Prompts: {len(json_content['video_prompts'])}")
    print(f"   • Manim Specs: {len(json_content['manim_prompts'])}")
    
    print(f"\n[3] COVERAGE ANALYSIS")
    coverage = analyze_coverage(md_elements, json_content, md_content)
    print(f"   • Headings Covered: {coverage['headings_covered']}/{len(md_elements['headings'])}")
    
    if coverage['headings_missing']:
        print(f"   • Missing Headings:")
        for h in coverage['headings_missing'][:5]:
            print(f"      - {h}")
    
    print(f"   • Tables: {coverage['tables_found']} found, {coverage['tables_referenced']} referenced")
    print(f"   • Images: {coverage['images_found']} found, {coverage['images_referenced']} referenced")
    print(f"   • Equations: {coverage['equations_found']} found, {coverage['equations_referenced']} referenced")
    print(f"   • Text Coverage (via pointers): {coverage['text_coverage_pct']}%")
    
    print(f"\n[4] FIDELITY VERDICT")
    if coverage['text_coverage_pct'] >= 80 and len(json_content['pointers']) > 0:
        print(f"   ✅ HIGH FIDELITY: {coverage['pointer_count']} pointers, {coverage['text_coverage_pct']}% coverage")
    elif coverage['text_coverage_pct'] >= 50:
        print(f"   ⚠️  MEDIUM FIDELITY: Some content may be missing or summarized")
    else:
        print(f"   ❌ LOW FIDELITY: Significant content missing")
    
    print(f"\n{'=' * 70}")

if __name__ == "__main__":
    generate_analysis()
