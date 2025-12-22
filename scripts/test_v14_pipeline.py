#!/usr/bin/env python3
"""
V1.4 Pipeline Test Script

This script tests the V1.4 Split Director pipeline end-to-end.
It can be run in different modes:
1. info_only: Just check pipeline info (no API calls)
2. dry_run: Call the dry-run-test endpoint (no LLM costs)
3. full_test: Run actual pipeline with LLMs (incurs costs)

Usage:
    python scripts/test_v14_pipeline.py --mode info_only
    python scripts/test_v14_pipeline.py --mode dry_run
    python scripts/test_v14_pipeline.py --mode full_test --skip-tts
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path

API_BASE = os.environ.get("API_BASE", "http://localhost:5000")

SAMPLE_MARKDOWN = """
# Photosynthesis: The Engine of Life

## Introduction
Photosynthesis is the process by which green plants, algae, and some bacteria convert light energy into chemical energy stored in glucose. This process is fundamental to life on Earth.

## The Light-Dependent Reactions
The light-dependent reactions occur in the thylakoid membranes of chloroplasts.

### Key Steps:
1. **Light Absorption**: Chlorophyll absorbs sunlight, primarily blue and red wavelengths
2. **Water Splitting**: Water molecules are split, releasing oxygen as a byproduct
3. **Electron Transport**: Energized electrons move through the electron transport chain
4. **ATP and NADPH Production**: Energy carriers are produced for the next stage

### The Equation:
6H₂O + Light Energy → 6O₂ + ATP + NADPH

## The Light-Independent Reactions (Calvin Cycle)
Also known as the Calvin Cycle, these reactions occur in the stroma of chloroplasts.

### Process Overview:
- Carbon dioxide is fixed by the enzyme RuBisCO
- ATP and NADPH from light reactions power the cycle
- Glucose is gradually built from carbon dioxide molecules

### The Complete Equation:
6CO₂ + 6H₂O + Light Energy → C₆H₁₂O₆ + 6O₂

## Factors Affecting Photosynthesis
Several environmental factors influence the rate of photosynthesis:

1. **Light Intensity**: More light generally means faster photosynthesis (up to a saturation point)
2. **Carbon Dioxide Concentration**: Higher CO₂ increases rate until other factors become limiting
3. **Temperature**: Optimal temperature varies by plant species (typically 25-35°C)
4. **Water Availability**: Drought stress reduces photosynthetic efficiency

## Example: Comparing C3 and C4 Plants
C4 plants like maize and sugarcane have evolved a specialized carbon fixation mechanism:
- C4 plants concentrate CO₂ in bundle sheath cells
- This reduces photorespiration losses
- C4 plants are more efficient in hot, dry conditions
- Examples: Corn, sugarcane, sorghum (common in tropical climates)

## Summary
Photosynthesis converts light energy to chemical energy through two main stages:
1. Light-dependent reactions produce ATP and NADPH
2. Light-independent reactions (Calvin Cycle) use these to fix CO₂ into glucose

This process sustains nearly all life on Earth and is crucial for understanding plant biology and agriculture.
"""


def print_header(text: str):
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)


def print_section(text: str):
    print(f"\n--- {text} ---")


def test_pipeline_info():
    """Test the pipeline info endpoint."""
    print_header("V1.4 Pipeline Information")
    
    try:
        response = requests.get(f"{API_BASE}/api/v14/pipeline-info", timeout=10)
        response.raise_for_status()
        info = response.json()
        
        print(f"\nPipeline Version: {info.get('version')}")
        print(f"Architecture: {info.get('architecture')}")
        
        print_section("Passes")
        for pass_id, description in info.get("passes", {}).items():
            print(f"  Pass {pass_id}: {description}")
        
        print_section("Models")
        for component, model in info.get("models", {}).items():
            print(f"  {component}: {model}")
        
        print_section("Retry Strategy")
        for component, retries in info.get("retry_strategy", {}).items():
            print(f"  {component}: structural={retries.get('structural')}, semantic={retries.get('semantic', 0)}")
        
        return True, info
        
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Cannot connect to API at {API_BASE}")
        print("Make sure the server is running (python api/app.py)")
        return False, None
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False, None


def test_dry_run():
    """Test the dry-run endpoint."""
    print_header("V1.4 Dry Run Test")
    
    try:
        response = requests.post(
            f"{API_BASE}/api/v14/dry-run-test",
            json={
                "markdown": SAMPLE_MARKDOWN,
                "subject": "Biology",
                "grade": "10"
            },
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        print(f"\nStatus: {result.get('status')}")
        print(f"Pipeline Version: {result.get('pipeline_version')}")
        
        print_section("Test Input")
        test_input = result.get("test_input", {})
        print(f"  Subject: {test_input.get('subject')}")
        print(f"  Grade: {test_input.get('grade')}")
        print(f"  Markdown Length: {test_input.get('markdown_length')} chars")
        
        print_section("Expected Output")
        expected = result.get("expected_output", {})
        
        topics = expected.get("topics", {})
        print(f"  Source Topic: {topics.get('source_topic')}")
        print(f"  Expected Topics: {len(topics.get('topics', []))}")
        for t in topics.get("topics", []):
            print(f"    - {t.get('title')} ({t.get('concept_type')}) → {t.get('suggested_renderer')}")
        
        sections = expected.get("sections", {})
        print(f"\n  From Content Director: {sections.get('from_content_director')}")
        print(f"  From Recap Director: {sections.get('from_recap_director')}")
        print(f"  Merge Order: {sections.get('merge_result_order')}")
        
        validation = expected.get("validation_criteria", {})
        print_section("Validation Criteria")
        print(f"  Memory: {validation.get('memory')}")
        print(f"  Recap: {validation.get('recap')}")
        
        print_section("Next Steps")
        for step in result.get("next_steps", []):
            print(f"  - {step}")
        
        return True, result
        
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Cannot connect to API at {API_BASE}")
        return False, None
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False, None


def test_full_pipeline(skip_tts: bool = True):
    """Test the full V1.4 pipeline with actual LLM calls."""
    print_header("V1.4 Full Pipeline Test")
    print(f"\nWARNING: This will incur LLM API costs!")
    print(f"Skip TTS: {skip_tts}")
    
    try:
        print("\nSubmitting job...")
        response = requests.post(
            f"{API_BASE}/api/v14/generate",
            json={
                "markdown": SAMPLE_MARKDOWN,
                "subject": "Biology",
                "grade": "10",
                "skip_tts": skip_tts
            },
            timeout=300
        )
        
        result = response.json()
        
        print(f"\nStatus: {result.get('status')}")
        print(f"Job ID: {result.get('job_id')}")
        
        if result.get("status") == "error":
            print_section("Error Details")
            print(f"  Error: {result.get('error')}")
            if result.get("traceback"):
                print(f"\n  Traceback:\n{result.get('traceback')}")
            return False, result
        
        print_section("Validation Results")
        validation = result.get("validation", {})
        print(f"  Has Errors: {validation.get('has_errors')}")
        print(f"  Section Count: {validation.get('section_count')}")
        print(f"  Total Segments: {validation.get('total_segments')}")
        
        if validation.get("errors"):
            print("\n  Errors:")
            for err in validation.get("errors", []):
                print(f"    - {err}")
        
        if validation.get("warnings"):
            print("\n  Warnings:")
            for warn in validation.get("warnings", []):
                print(f"    - {warn}")
        
        print_section("Analytics")
        analytics = result.get("analytics", {})
        if analytics:
            print(f"  Total Tokens: {analytics.get('total_tokens', 'N/A')}")
            print(f"  Total Duration: {analytics.get('total_duration_seconds', 'N/A')}s")
        
        print_section("Presentation Structure")
        presentation = result.get("presentation", {})
        print(f"  Spec Version: {presentation.get('spec_version')}")
        print(f"  Title: {presentation.get('title')}")
        print(f"  Subject: {presentation.get('subject')}")
        
        sections = presentation.get("sections", [])
        print(f"\n  Sections ({len(sections)}):")
        for s in sections:
            section_type = s.get("section_type")
            renderer = s.get("renderer")
            seg_count = len(s.get("narration", {}).get("segments", []))
            
            extra = ""
            if section_type == "memory":
                fc_count = len(s.get("flashcards", []))
                extra = f", flashcards={fc_count}"
            elif section_type == "recap":
                vp_count = len(s.get("video_prompts", []))
                extra = f", video_prompts={vp_count}"
            
            print(f"    - {s.get('section_id')}: {section_type} (renderer={renderer}, segments={seg_count}{extra})")
        
        print_section("Output")
        print(f"  Output Path: {result.get('output_path')}")
        
        return True, result
        
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Cannot connect to API at {API_BASE}")
        return False, None
    except requests.exceptions.Timeout:
        print(f"\n[ERROR] Request timed out (pipeline may still be running)")
        return False, None
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False, None


def generate_report(results: dict):
    """Generate a summary report."""
    print_header("V1.4 PIPELINE TEST REPORT")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\nGenerated: {timestamp}")
    print(f"API Base: {API_BASE}")
    
    print_section("Test Results Summary")
    
    for test_name, (success, data) in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {test_name}")
    
    all_passed = all(success for success, _ in results.values())
    
    print(f"\n{'='*60}")
    if all_passed:
        print(" ALL TESTS PASSED")
    else:
        print(" SOME TESTS FAILED")
    print(f"{'='*60}")
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Test V1.4 Split Director Pipeline")
    parser.add_argument(
        "--mode",
        choices=["info_only", "dry_run", "full_test"],
        default="dry_run",
        help="Test mode: info_only (no API calls), dry_run (structure check), full_test (actual LLM calls)"
    )
    parser.add_argument(
        "--skip-tts",
        action="store_true",
        default=True,
        help="Skip TTS generation in full_test mode (default: True)"
    )
    parser.add_argument(
        "--api-base",
        default=None,
        help="API base URL (default: http://localhost:5000)"
    )
    
    args = parser.parse_args()
    
    global API_BASE
    if args.api_base:
        API_BASE = args.api_base
    
    print(f"\nV1.4 Pipeline Test Script")
    print(f"Mode: {args.mode}")
    print(f"API: {API_BASE}")
    
    results = {}
    
    results["pipeline_info"] = test_pipeline_info()
    
    if args.mode == "dry_run" or args.mode == "full_test":
        results["dry_run"] = test_dry_run()
    
    if args.mode == "full_test":
        results["full_pipeline"] = test_full_pipeline(skip_tts=args.skip_tts)
    
    success = generate_report(results)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
