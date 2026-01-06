import json
import re
from pathlib import Path

JOB_ID = "6b12114f"
JOB_DIR = Path(f"player/jobs/{JOB_ID}")
JSON_PATH = JOB_DIR / "presentation.json"
MD_PATH = JOB_DIR / "source_markdown.md"

def analyze_fidelity():
    if not JSON_PATH.exists() or not MD_PATH.exists():
        return {"error": "Missing files"}

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        presentation = json.load(f)
    
    with open(MD_PATH, 'r', encoding='utf-8') as f:
        markdown_text = f.read()

    # 1. Parse Markdown into topics
    topics = []
    current_topic = None
    lines = markdown_text.split('\n')
    
    for line in lines:
        if line.strip().startswith('#'):
            if current_topic:
                topics.append(current_topic)
            
            level = len(line.strip().split(' ')[0])
            title = line.strip().lstrip('#').strip()
            current_topic = {
                'title': title,
                'content_lines': [],
                'tables': 0,
                'images': 0
            }
        elif current_topic:
            stripped = line.strip()
            if stripped:
                current_topic['content_lines'].append(stripped)
                if '|' in stripped:
                    current_topic['tables'] += 1
                if stripped.startswith('!['):
                    current_topic['images'] += 1

    if current_topic:
        topics.append(current_topic)

    # 2. Map JSON sections
    json_sections = presentation.get('sections', [])
    
    analysis = []

    for i, topic in enumerate(topics):
        topic_analysis = {
            "topic_number": i + 1,
            "markdown_title": topic['title'],
            "json_match": None,
            "pointer_count": 0,
            "segment_count": 0,
            "tables_in_md": topic['tables'],
            "images_in_md": topic['images'],
            "status": "MISSING"
        }
        
        # Search for this topic in JSON sections
        found_section = None
        for sec in json_sections:
            sec_title = sec.get('title', '').lower()
            if topic['title'].lower() in sec_title or sec_title in topic['title'].lower():
                found_section = sec
                break
        
        if not found_section:
            for sec in json_sections:
                for seg in sec.get('narration', {}).get('segments', []):
                    if topic['title'].lower() in seg.get('text', '').lower():
                        found_section = sec
                        break
                if found_section: break

        if found_section:
            topic_analysis["json_match"] = found_section.get('title')
            topic_analysis["status"] = "MATCHED"
            segments = found_section.get('narration', {}).get('segments', [])
            topic_analysis["segment_count"] = len(segments)
            pointers = [s.get('visual_content', {}).get('markdown_pointer') for s in segments if s.get('visual_content', {}).get('markdown_pointer')]
            topic_analysis["pointer_count"] = len(pointers)

        analysis.append(topic_analysis)

    return analysis

if __name__ == "__main__":
    result = analyze_fidelity()
    with open('scripts/detailed_fidelity_report.json', 'w') as f:
        json.dump(result, f, indent=2)
    print("DONE")
