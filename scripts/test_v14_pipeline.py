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
    python scripts/test_v14_pipeline.py --mode full_test --tts-provider pyttsx3
    python scripts/test_v14_pipeline.py --mode full_test --markdown-file attached_assets/Sample_subjects_v2_1766399532763.md
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


def load_markdown_file(file_path: str) -> str:
    """Load markdown content from a file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Markdown file not found: {file_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


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


def test_dry_run(markdown: str = None):
    """Test the dry-run endpoint."""
    print_header("V1.4 Dry Run Test")
    
    try:
        response = requests.post(
            f"{API_BASE}/api/v14/dry-run-test",
            json={
                "markdown": markdown or SAMPLE_MARKDOWN,
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


def test_full_pipeline(
    markdown: str = None,
    subject: str = "Biology",
    grade: str = "10",
    skip_wan: bool = True,
    tts_provider: str = "pyttsx3"
):
    """Test the full V1.4 pipeline with actual LLM calls."""
    print_header("V1.4 Full Pipeline Test")
    print(f"\nWARNING: This will incur LLM API costs!")
    print(f"TTS Provider: {tts_provider}")
    print(f"Skip WAN: {skip_wan}")
    print(f"Subject: {subject}")
    print(f"Grade: {grade}")
    
    content = markdown or SAMPLE_MARKDOWN
    print(f"Markdown Length: {len(content)} chars")
    
    try:
        print("\nSubmitting job...")
        start_time = datetime.now()
        
        response = requests.post(
            f"{API_BASE}/api/v14/generate",
            json={
                "markdown": content,
                "subject": subject,
                "grade": grade,
                "skip_wan": skip_wan,
                "tts_provider": tts_provider
            },
            timeout=600
        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"Response received in {elapsed:.2f}s")
        
        result = response.json()
        
        print(f"\nStatus: {result.get('status')}")
        print(f"Job ID: {result.get('job_id', 'N/A')}")
        
        if result.get("status") == "error":
            print_section("Error Details")
            print(f"  Error: {result.get('error')}")
            if result.get("traceback"):
                print(f"\n  Traceback:\n{result.get('traceback')}")
            
            error_msg = result.get('error', '')
            if "Recap Director" in error_msg:
                print_section("Recap Director Failure Analysis")
                print("  The Recap Director failed semantic validation.")
                print("  This is an LLM prompt engineering issue, not a TTS code issue.")
                print("  The TTS code path was not reached due to earlier pipeline failure.")
            elif "Content Director" in error_msg:
                print_section("Content Director Failure Analysis")
                print("  The Content Director failed validation.")
                print("  The TTS code path was not reached due to earlier pipeline failure.")
            
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
        
        metadata = presentation.get("metadata", {})
        if metadata:
            print(f"\n  Metadata:")
            print(f"    TTS Provider: {metadata.get('tts_provider')}")
            print(f"    Total Duration: {metadata.get('total_duration_seconds')}s")
            print(f"    TTS Segments: {metadata.get('tts_segments_processed')}")
        
        sections = presentation.get("sections", [])
        print(f"\n  Sections ({len(sections)}):")
        for s in sections:
            section_type = s.get("section_type")
            renderer = s.get("renderer")
            seg_count = len(s.get("narration", {}).get("segments", []))
            duration = s.get("narration", {}).get("total_duration_seconds", 0)
            
            extra = ""
            if section_type == "memory":
                fc_count = len(s.get("flashcards", []))
                extra = f", flashcards={fc_count}"
            elif section_type == "recap":
                vp_count = len(s.get("video_prompts", []))
                extra = f", video_prompts={vp_count}"
            
            print(f"    - {s.get('section_id')}: {section_type} (renderer={renderer}, segments={seg_count}, duration={duration:.1f}s{extra})")
        
        print_section("Output")
        print(f"  Output Path: {result.get('output_path')}")
        print(f"  TTS Provider Used: {result.get('tts_provider')}")
        print(f"  Skip WAN: {result.get('skip_wan')}")
        
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


def generate_report(results: dict, output_file: str = None):
    """Generate a summary report."""
    print_header("V1.4 PIPELINE TEST REPORT")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\nGenerated: {timestamp}")
    print(f"API Base: {API_BASE}")
    
    print_section("Test Results Summary")
    
    report_lines = [
        f"# V1.4 Pipeline Test Report",
        f"Generated: {timestamp}",
        f"API Base: {API_BASE}",
        "",
        "## Test Results",
        ""
    ]
    
    for test_name, (success, data) in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {test_name}")
        report_lines.append(f"- **{test_name}**: {status}")
    
    all_passed = all(success for success, _ in results.values())
    
    print(f"\n{'='*60}")
    if all_passed:
        print(" ALL TESTS PASSED")
        report_lines.append("\n## Summary\n**ALL TESTS PASSED**")
    else:
        print(" SOME TESTS FAILED")
        report_lines.append("\n## Summary\n**SOME TESTS FAILED**")
    print(f"{'='*60}")
    
    if "full_pipeline" in results:
        success, data = results["full_pipeline"]
        if data and success:
            report_lines.extend([
                "",
                "## Full Pipeline Details",
                f"- Job ID: {data.get('job_id')}",
                f"- Output Path: {data.get('output_path')}",
                f"- TTS Provider: {data.get('tts_provider')}"
            ])
            
            validation = data.get("validation", {})
            report_lines.extend([
                "",
                "### Validation",
                f"- Section Count: {validation.get('section_count')}",
                f"- Total Segments: {validation.get('total_segments')}",
                f"- Errors: {len(validation.get('errors', []))}",
                f"- Warnings: {len(validation.get('warnings', []))}"
            ])
            
            presentation = data.get("presentation", {})
            metadata = presentation.get("metadata", {})
            report_lines.extend([
                "",
                "### Duration",
                f"- Total Duration: {metadata.get('total_duration_seconds')}s",
                f"- Segments Processed: {metadata.get('tts_segments_processed')}"
            ])
    
    if output_file:
        output_path = Path(output_file)
        with open(output_path, "w") as f:
            f.write("\n".join(report_lines))
        print(f"\nReport saved to: {output_path}")
    
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
        "--markdown-file",
        default=None,
        help="Path to markdown file to use instead of sample content"
    )
    parser.add_argument(
        "--subject",
        default="Biology",
        help="Subject area (default: Biology)"
    )
    parser.add_argument(
        "--grade",
        default="10",
        help="Grade level (default: 10)"
    )
    parser.add_argument(
        "--tts-provider",
        choices=["narakeet", "pyttsx3", "estimate"],
        default="pyttsx3",
        help="TTS provider: narakeet (production), pyttsx3 (local/dry run), estimate (word-count based)"
    )
    parser.add_argument(
        "--skip-wan",
        action="store_true",
        default=True,
        help="Skip WAN video rendering (default: True)"
    )
    parser.add_argument(
        "--api-base",
        default=None,
        help="API base URL (default: http://localhost:5000)"
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Path to save test report (optional)"
    )
    
    args = parser.parse_args()
    
    global API_BASE
    if args.api_base:
        API_BASE = args.api_base
    
    markdown_content = None
    if args.markdown_file:
        try:
            markdown_content = load_markdown_file(args.markdown_file)
            print(f"Loaded markdown from: {args.markdown_file}")
            print(f"Content length: {len(markdown_content)} chars")
        except FileNotFoundError as e:
            print(f"[ERROR] {e}")
            sys.exit(1)
    
    print(f"\nV1.4 Pipeline Test Script")
    print(f"Mode: {args.mode}")
    print(f"API: {API_BASE}")
    if args.mode == "full_test":
        print(f"TTS Provider: {args.tts_provider}")
        print(f"Skip WAN: {args.skip_wan}")
    
    results = {}
    
    results["pipeline_info"] = test_pipeline_info()
    
    if args.mode == "dry_run" or args.mode == "full_test":
        results["dry_run"] = test_dry_run(markdown=markdown_content)
    
    if args.mode == "full_test":
        results["full_pipeline"] = test_full_pipeline(
            markdown=markdown_content,
            subject=args.subject,
            grade=args.grade,
            skip_wan=args.skip_wan,
            tts_provider=args.tts_provider
        )
    
    success = generate_report(results, output_file=args.report)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
