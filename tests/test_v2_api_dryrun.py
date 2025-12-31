#!/usr/bin/env python
"""
V2 API Dry Run Test

Simulates the full API flow with the 13-page PDF markdown.
Tests: Raw markdown → V2 UnifiedContentGenerator → Player-compatible output
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.unified_content_generator import (
    generate_presentation,
    transform_to_player_schema,
    GeneratorConfig,
    validate_schema
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_v2_dry_run(markdown_path: str, output_dir: str = "tests/output"):
    """
    Run a complete V2 dry run simulating API flow.
    
    Flow:
    1. Load raw markdown (simulates Datalab output)
    2. Call UnifiedContentGenerator (single LLM call)
    3. Validate schema (non-LLM)
    4. Transform to player schema
    5. Save output
    """
    start_time = time.time()
    
    print("=" * 70)
    print("V2 API DRY RUN TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Step 1: Load markdown
    print("STEP 1: Load Raw Markdown")
    print("-" * 40)
    with open(markdown_path) as f:
        markdown_content = f.read()
    
    word_count = len(markdown_content.split())
    char_count = len(markdown_content)
    print(f"  Source: {markdown_path}")
    print(f"  Size: {char_count:,} chars, {word_count:,} words")
    print()
    
    # Step 2: Call UnifiedContentGenerator
    print("STEP 2: UnifiedContentGenerator (LLM Call)")
    print("-" * 40)
    
    config = GeneratorConfig(
        model="google/gemini-2.5-pro-preview",
        max_retries=3,
        temperature=0.7
    )
    
    llm_start = time.time()
    
    try:
        raw_output = generate_presentation(
            markdown_content=markdown_content,
            subject="Biology",
            grade="Grade 10",
            images_list="None",
            config=config
        )
        llm_time = time.time() - llm_start
        print(f"  Status: SUCCESS")
        print(f"  LLM Time: {llm_time:.2f}s")
        print(f"  Sections Generated: {len(raw_output.get('sections', []))}")
    except Exception as e:
        print(f"  Status: FAILED")
        print(f"  Error: {e}")
        return None
    
    print()
    
    # Step 3: Schema Validation
    print("STEP 3: Schema Validation (Non-LLM)")
    print("-" * 40)
    is_valid, errors = validate_schema(raw_output)
    print(f"  Valid: {is_valid}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for e in errors[:3]:
            print(f"    - {e}")
    print()
    
    # Step 4: Transform to Player Schema
    print("STEP 4: Transform to Player Schema")
    print("-" * 40)
    player_output = transform_to_player_schema(
        raw_output, 
        subject="Biology", 
        grade="10"
    )
    
    # Calculate stats
    sections = player_output.get("sections", [])
    total_segments = sum(
        len(s.get("narration", {}).get("segments", []))
        for s in sections
    )
    total_words = sum(
        len(s.get("narration", {}).get("full_text", "").split())
        for s in sections
    )
    
    section_types = {}
    for s in sections:
        t = s.get("section_type", "unknown")
        section_types[t] = section_types.get(t, 0) + 1
    
    print(f"  Sections: {len(sections)}")
    print(f"  Segments: {total_segments}")
    print(f"  Words: {total_words:,}")
    print(f"  Section Types: {section_types}")
    
    # Check special sections
    quiz_count = sum(
        len(s.get("quiz_data", {}).get("questions", []))
        for s in sections if s.get("quiz_data")
    )
    flashcard_count = sum(
        len(s.get("flashcards", []))
        for s in sections if s.get("flashcards")
    )
    video_prompt_count = sum(
        len(s.get("video_prompts", []))
        for s in sections if s.get("video_prompts")
    )
    
    print(f"  Quiz Questions: {quiz_count}")
    print(f"  Flashcards: {flashcard_count}")
    print(f"  Video Prompts: {video_prompt_count}")
    print()
    
    # Step 5: Save Output
    print("STEP 5: Save Output")
    print("-" * 40)
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save raw output
    raw_file = Path(output_dir) / f"v2_dryrun_raw_{timestamp}.json"
    with open(raw_file, "w") as f:
        json.dump(raw_output, f, indent=2)
    print(f"  Raw: {raw_file}")
    
    # Save player output
    player_file = Path(output_dir) / f"v2_dryrun_player_{timestamp}.json"
    with open(player_file, "w") as f:
        json.dump(player_output, f, indent=2)
    print(f"  Player: {player_file}")
    print()
    
    # Summary
    total_time = time.time() - start_time
    
    print("=" * 70)
    print("DRY RUN SUMMARY")
    print("=" * 70)
    print(f"""
┌────────────────────────────────────────────────────────────────────┐
│ METRIC                          │ VALUE                            │
├─────────────────────────────────┼──────────────────────────────────┤
│ Total Time                      │ {total_time:.2f}s                          │
│ LLM Calls                       │ 1                                │
│ LLM Time                        │ {llm_time:.2f}s                          │
│ Schema Valid                    │ {is_valid}                            │
├─────────────────────────────────┼──────────────────────────────────┤
│ Input Words                     │ {word_count:,}                          │
│ Output Sections                 │ {len(sections)}                              │
│ Output Segments                 │ {total_segments}                              │
│ Output Words                    │ {total_words:,}                          │
├─────────────────────────────────┼──────────────────────────────────┤
│ Quiz Questions                  │ {quiz_count}                               │
│ Flashcards                      │ {flashcard_count}                               │
│ Video Prompts                   │ {video_prompt_count}                               │
└────────────────────────────────────────────────────────────────────┘

COMPARISON WITH CURRENT PIPELINE:
  Current V1.5: 18-22 LLM calls
  V2 Unified:   1 LLM call
  Reduction:    95%+
""")
    
    return player_output


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="V2 API Dry Run Test")
    parser.add_argument(
        "--markdown",
        default="player/jobs/5f13fb49/source_markdown.md",
        help="Path to markdown file"
    )
    parser.add_argument(
        "--output-dir",
        default="tests/output",
        help="Output directory"
    )
    
    args = parser.parse_args()
    run_v2_dry_run(args.markdown, args.output_dir)
