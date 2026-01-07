"""
V2.5 Director Bible Validation Script
Validates presentation.json against the Director Bible requirements.

Usage: python verify_job_content.py <JOB_ID>
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import Counter

# Director Bible Section Requirements
SECTION_REQUIREMENTS = {
    "intro": {
        "count": 1,
        "min_words": 40,
        "max_words": 60,
        "visual": "avatar_only",
        "required": True
    },
    "summary": {
        "count": 1,
        "description": "Learning objectives/bullet list",
        "visual": "text",
        "required": True
    },
    "content": {
        "min_count": 1,
        "description": "Main teaching (Teach -> Show pattern)",
        "visual": "mixed (manim/wan_video)",
        "required": True
    },
    "example": {
        "description": "Problem walkthrough",
        "visual": "manim/video",
        "required": False  # Optional
    },
    "quiz": {
        "description": "Q&A with 3-step dance (Introduce, Pause, Reveal)",
        "visual": "text",
        "required": False  # Optional depending on content
    },
    "memory": {
        "count": 5,  # Exactly 5 flashcards
        "description": "Flashcards for retention",
        "visual": "text",
        "required": True
    },
    "recap": {
        "count": 5,  # Exactly 5 segments
        "description": "Cinematic closure with video",
        "visual": "wan_video",
        "required": True
    }
}

def classify_section(section: Dict) -> str:
    """Classify section type based on content."""
    title = section.get("title", "").lower()
    section_type = section.get("section_type", "").lower()
    
    # Direct type match
    if section_type:
        return section_type
    
    # Title-based classification
    if "intro" in title or "introduction" in title:
        return "intro"
    elif "summary" in title or "learning objective" in title or "what we will learn" in title:
        return "summary"
    elif "recap" in title or "conclusion" in title or "closing" in title:
        return "recap"
    elif "memory" in title or "flashcard" in title:
        return "memory"
    elif "quiz" in title or "question" in title or "exercise" in title:
        return "quiz"
    elif "example" in title or "problem" in title or "solve" in title:
        return "example"
    else:
        return "content"

def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())

def validate_job(job_id: str) -> Dict:
    """Validate job against Director Bible."""
    job_dir = Path(f"player/jobs/{job_id}")
    pres_file = job_dir / "presentation.json"
    md_file = job_dir / "source_markdown.md"
    
    results = {
        "job_id": job_id,
        "status": "valid",
        "errors": [],
        "warnings": [],
        "stats": {}
    }
    
    # Check files exist
    if not pres_file.exists():
        results["errors"].append(f"presentation.json not found")
        results["status"] = "invalid"
        return results
    
    # Load presentation
    with open(pres_file, 'r', encoding='utf-8') as f:
        presentation = json.load(f)
    
    # Load markdown if exists
    md_content = ""
    if md_file.exists():
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
    
    sections = presentation.get("sections", [])
    metadata = presentation.get("metadata", {})
    
    # Basic stats
    results["stats"]["total_sections"] = len(sections)
    results["stats"]["markdown_chars"] = len(md_content)
    results["stats"]["presentation_bytes"] = pres_file.stat().st_size
    results["stats"]["pipeline"] = metadata.get("pipeline_mode", "unknown")
    
    # Classify sections
    section_types = []
    for s in sections:
        s_type = classify_section(s)
        section_types.append(s_type)
    
    type_counts = Counter(section_types)
    results["stats"]["section_types"] = dict(type_counts)
    
    # Count narration segments
    total_segments = 0
    total_words = 0
    for s in sections:
        segs = s.get("narration", {}).get("segments", [])
        total_segments += len(segs)
        for seg in segs:
            total_words += count_words(seg.get("text", ""))
    
    results["stats"]["total_segments"] = total_segments
    results["stats"]["total_words"] = total_words
    
    # Check renderers
    renderers = Counter([s.get("visual", {}).get("renderer", "none") for s in sections])
    results["stats"]["renderers"] = dict(renderers)
    
    # Check manim_spec fields
    manim_count = 0
    for s in sections:
        if s.get("visual", {}).get("manim_spec"):
            manim_count += 1
    results["stats"]["sections_with_manim_spec"] = manim_count
    
    # Check video_prompts
    wan_count = 0
    for s in sections:
        if s.get("visual", {}).get("video_prompts"):
            wan_count += 1
    results["stats"]["sections_with_video_prompts"] = wan_count
    
    # === DIRECTOR BIBLE VALIDATION ===
    
    # 1. Check for required sections
    if type_counts.get("intro", 0) < 1:
        results["warnings"].append("Missing INTRO section (should have welcoming opener)")
    
    if type_counts.get("summary", 0) < 1:
        results["warnings"].append("Missing SUMMARY section (learning objectives)")
    
    if type_counts.get("content", 0) < 1:
        results["errors"].append("Missing CONTENT sections (main teaching)")
        results["status"] = "invalid"
    
    # 2. Memory section check (should have 5 flashcards)
    memory_count = type_counts.get("memory", 0)
    if memory_count > 0 and memory_count != 5:
        results["warnings"].append(f"Memory section has {memory_count} items (Bible requires exactly 5)")
    
    # 3. Recap section check (should have 5 segments)
    recap_count = type_counts.get("recap", 0)
    if recap_count > 0 and recap_count != 5:
        results["warnings"].append(f"Recap section has {recap_count} items (Bible requires exactly 5)")
    
    # 4. Check for manim_spec in math-related content
    math_keywords = ["calculate", "formula", "equation", "solve", "graph", "arithmetic"]
    might_need_manim = any(kw in md_content.lower() for kw in math_keywords)
    if might_need_manim and manim_count == 0:
        results["warnings"].append("Document contains math content but no manim_spec generated")
    
    # 5. Check audio files
    audio_dir = job_dir / "audio"
    if audio_dir.exists():
        audio_files = list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.wav"))
        non_empty = [f for f in audio_files if f.stat().st_size > 1000]
        results["stats"]["audio_files"] = len(audio_files)
        results["stats"]["audio_with_content"] = len(non_empty)
        
        if len(non_empty) < total_segments * 0.5:
            results["warnings"].append(f"Only {len(non_empty)}/{total_segments} audio files generated")
    else:
        results["stats"]["audio_files"] = 0
        results["stats"]["audio_with_content"] = 0
        results["warnings"].append("No audio directory found")
    
    # 6. Check video files
    video_dir = job_dir / "videos"
    if video_dir.exists():
        video_files = list(video_dir.glob("*.mp4"))
        non_empty = [f for f in video_files if f.stat().st_size > 10000]
        results["stats"]["video_files"] = len(video_files)
        results["stats"]["video_with_content"] = len(non_empty)
    else:
        results["stats"]["video_files"] = 0
        results["stats"]["video_with_content"] = 0
    
    # 7. Check avatars
    avatar_dir = job_dir / "avatars"
    if avatar_dir.exists():
        avatar_files = list(avatar_dir.glob("*.mp4"))
        results["stats"]["avatar_files"] = len(avatar_files)
    else:
        results["stats"]["avatar_files"] = 0
    
    # Final status
    if results["errors"]:
        results["status"] = "invalid"
    elif results["warnings"]:
        results["status"] = "valid_with_warnings"
    else:
        results["status"] = "valid"
    
    return results

def print_results(results: Dict):
    """Pretty print validation results."""
    print("=" * 70)
    print(f"JOB VALIDATION: {results['job_id']}")
    print(f"STATUS: {results['status'].upper()}")
    print("=" * 70)
    
    print("\n📊 STATISTICS:")
    stats = results["stats"]
    print(f"  Total Sections:     {stats.get('total_sections', 0)}")
    print(f"  Total Segments:     {stats.get('total_segments', 0)}")
    print(f"  Total Words:        {stats.get('total_words', 0):,}")
    print(f"  Markdown Source:    {stats.get('markdown_chars', 0):,} chars")
    print(f"  Presentation JSON:  {stats.get('presentation_bytes', 0):,} bytes")
    print(f"  Pipeline:           {stats.get('pipeline', 'unknown')}")
    
    print("\n📋 SECTION TYPES:")
    for stype, count in stats.get("section_types", {}).items():
        print(f"  {stype:15} : {count}")
    
    print("\n🎬 RENDERERS:")
    for renderer, count in stats.get("renderers", {}).items():
        print(f"  {renderer:15} : {count}")
    
    print("\n📁 ASSETS:")
    print(f"  Manim Specs:        {stats.get('sections_with_manim_spec', 0)}")
    print(f"  Video Prompts:      {stats.get('sections_with_video_prompts', 0)}")
    print(f"  Audio Files:        {stats.get('audio_with_content', 0)}/{stats.get('audio_files', 0)}")
    print(f"  Video Files:        {stats.get('video_with_content', 0)}/{stats.get('video_files', 0)}")
    print(f"  Avatar Files:       {stats.get('avatar_files', 0)}")
    
    if results["errors"]:
        print("\n❌ ERRORS:")
        for err in results["errors"]:
            print(f"  • {err}")
    
    if results["warnings"]:
        print("\n⚠️ WARNINGS:")
        for warn in results["warnings"]:
            print(f"  • {warn}")
    
    if results["status"] == "valid":
        print("\n✅ JOB PASSED ALL VALIDATIONS!")
    
    print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_job_content.py <JOB_ID>")
        print("Example: python verify_job_content.py 4ee21a06")
        sys.exit(1)
    
    job_id = sys.argv[1]
    results = validate_job(job_id)
    print_results(results)
