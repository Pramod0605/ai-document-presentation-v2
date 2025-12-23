#!/usr/bin/env python3
"""
V1.4 Pipeline Test Runner

Runs comprehensive tests against all test input files and validates:
- Renderer selection (manim vs video vs remotion)
- manim_scene_spec generation for math/physics
- visual_beats presence for manim/video sections
- Analytics tracking (tokens, cost, duration)
- Segment duration normalization
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.validate_display_layer import validate_presentation_dict

API_BASE = "http://localhost:5000"

TEST_CONFIGS = [
    {
        "name": "Math Calculus (Manim)",
        "file": "test_inputs/test_math_calculus.md",
        "subject": "Mathematics",
        "grade": "Grade 12",
        "skip_wan": True,
        "expected_renderers": ["remotion", "manim"],
        "require_manim_spec": True
    },
    {
        "name": "Physics Motion (Manim)",
        "file": "test_inputs/test_physics_motion.md",
        "subject": "Physics",
        "grade": "Grade 11",
        "skip_wan": True,
        "expected_renderers": ["remotion", "manim"],
        "require_manim_spec": True
    },
    {
        "name": "Biology Cells (Video/WAN)",
        "file": "test_inputs/test_biology_cells.md",
        "subject": "Biology",
        "grade": "Grade 10",
        "skip_wan": True,
        "expected_renderers": ["remotion", "video"],
        "require_manim_spec": False
    },
    {
        "name": "Chemistry Reactions (Mixed)",
        "file": "test_inputs/test_chemistry_reactions.md",
        "subject": "Chemistry",
        "grade": "Grade 11",
        "skip_wan": True,
        "expected_renderers": ["remotion", "manim", "video"],
        "require_manim_spec": True
    }
]


def load_markdown(filepath: str) -> str:
    """Load markdown content from file."""
    with open(filepath, 'r') as f:
        return f.read()


def run_test(config: dict) -> dict:
    """Run a single test and return results."""
    print(f"\n{'='*60}")
    print(f"TEST: {config['name']}")
    print(f"{'='*60}")
    
    results = {
        "name": config["name"],
        "success": False,
        "errors": [],
        "warnings": [],
        "sections": [],
        "analytics": None,
        "duration": 0,
        "display_validation": None,
        "presentation": None
    }
    
    try:
        markdown = load_markdown(config["file"])
    except FileNotFoundError:
        results["errors"].append(f"File not found: {config['file']}")
        return results
    
    payload = {
        "markdown": markdown,
        "subject": config["subject"],
        "grade": config["grade"],
        "skip_wan": config.get("skip_wan", True)
    }
    
    start_time = time.time()
    
    try:
        print(f"Sending request to /api/v14/generate...")
        response = requests.post(
            f"{API_BASE}/api/v14/generate",
            json=payload,
            timeout=300
        )
        
        results["duration"] = time.time() - start_time
        print(f"Response received in {results['duration']:.1f}s (status: {response.status_code})")
        
        if response.status_code != 200:
            results["errors"].append(f"HTTP {response.status_code}: {response.text[:500]}")
            return results
        
        data = response.json()
        
        if "error" in data:
            results["errors"].append(f"API Error: {data['error']}")
            return results
        
        presentation = data.get("presentation", {})
        results["analytics"] = data.get("analytics", {})
        results["presentation"] = presentation
        
        sections = presentation.get("sections", [])
        print(f"Sections generated: {len(sections)}")
        
        for section in sections:
            section_info = {
                "section_id": section.get("section_id"),
                "section_type": section.get("section_type"),
                "renderer": section.get("renderer"),
                "has_manim_spec": "manim_scene_spec" in section,
                "visual_beats_count": len(section.get("visual_beats", [])),
                "segment_count": len(section.get("narration", {}).get("segments", [])),
                "total_duration": 0
            }
            
            for seg in section.get("narration", {}).get("segments", []):
                dur = seg.get("duration_estimate", 0) or seg.get("duration_seconds", 0)
                section_info["total_duration"] += dur
            
            results["sections"].append(section_info)
            
            renderer = section.get("renderer")
            section_type = section.get("section_type")
            
            if renderer == "manim" and not section_info["has_manim_spec"]:
                results["errors"].append(
                    f"ISS-109 FAIL: {section_info['section_id']} has renderer=manim but no manim_scene_spec"
                )
            
            if renderer in ["manim", "video"] and section_info["visual_beats_count"] == 0:
                if section_type not in ["memory", "recap"]:
                    results["warnings"].append(
                        f"{section_info['section_id']} has renderer={renderer} but 0 visual_beats"
                    )
            
            if section_info["total_duration"] == 0 and section_info["segment_count"] > 0:
                results["errors"].append(
                    f"ISS-107 FAIL: {section_info['section_id']} has {section_info['segment_count']} segments but duration=0"
                )
        
        analytics = results["analytics"]
        if analytics:
            cd_analytics = analytics.get("content_director", {})
            if cd_analytics.get("tokens", 0) == 0:
                results["errors"].append("ISS-110 FAIL: Content Director tokens = 0")
            else:
                print(f"Content Director: {cd_analytics.get('tokens', 0)} tokens, ${cd_analytics.get('cost_usd', 0):.4f}")
        
        required = {"intro", "summary", "memory", "recap"}
        found_types = {s.get("section_type") for s in sections}
        missing = required - found_types
        if missing:
            results["errors"].append(f"Missing required sections: {missing}")
        
        content_count = sum(1 for s in sections if s.get("section_type") == "content")
        if content_count == 0:
            results["errors"].append("No content sections generated")
        else:
            print(f"Content sections: {content_count}")
        
        memory_sections = [s for s in sections if s.get("section_type") == "memory"]
        if memory_sections:
            flashcards = memory_sections[0].get("flashcards", [])
            if len(flashcards) < 5:
                results["warnings"].append(f"Memory section has {len(flashcards)} flashcards (expected 5)")
        
        print("\nRunning Display Layer Validation...")
        display_success, display_errors, display_warnings, display_stats = validate_presentation_dict(presentation)
        
        if not display_success:
            for err in display_errors:
                results["errors"].append(f"DISPLAY: {err}")
        
        for warn in display_warnings:
            results["warnings"].append(f"DISPLAY: {warn}")
        
        results["display_validation"] = {
            "success": display_success,
            "errors": display_errors,
            "warnings": display_warnings,
            "stats": display_stats
        }
        
        if display_success:
            print(f"Display Layer Validation: PASS ({display_stats['total_segments']} segments, {display_stats['total_duration']:.1f}s)")
        else:
            print(f"Display Layer Validation: FAIL ({len(display_errors)} errors)")
        
        results["success"] = len(results["errors"]) == 0
        
    except requests.exceptions.Timeout:
        results["errors"].append("Request timed out after 300s")
    except requests.exceptions.ConnectionError:
        results["errors"].append("Connection failed - is server running?")
    except Exception as e:
        results["errors"].append(f"Unexpected error: {e}")
    
    return results


def print_summary(all_results: list):
    """Print test summary."""
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in all_results if r["success"])
    total = len(all_results)
    
    print(f"\nPassed: {passed}/{total}")
    
    for result in all_results:
        status = "PASS" if result["success"] else "FAIL"
        print(f"\n[{status}] {result['name']} ({result['duration']:.1f}s)")
        
        if result["sections"]:
            print(f"  Sections: {len(result['sections'])}")
            for s in result["sections"]:
                manim_str = " [manim_spec]" if s["has_manim_spec"] else ""
                print(f"    - {s['section_type']}: {s['renderer']}{manim_str}, {s['visual_beats_count']} beats, {s['total_duration']:.1f}s")
        
        for error in result["errors"]:
            print(f"  ERROR: {error}")
        
        for warning in result["warnings"]:
            print(f"  WARNING: {warning}")
    
    print("\n" + "="*70)
    if passed == total:
        print("ALL TESTS PASSED")
    else:
        print(f"TESTS FAILED: {total - passed}")
    print("="*70)


def main():
    """Run all tests."""
    print("V1.4 Pipeline Test Runner")
    print("="*70)
    
    try:
        health = requests.get(f"{API_BASE}/api/health", timeout=5)
        if health.status_code != 200:
            print("ERROR: Server health check failed")
            sys.exit(1)
        print("Server health check: OK")
    except:
        print("ERROR: Cannot connect to server at", API_BASE)
        print("Make sure the server is running: python api/app.py")
        sys.exit(1)
    
    test_filter = sys.argv[1] if len(sys.argv) > 1 else None
    
    configs = TEST_CONFIGS
    if test_filter:
        configs = [c for c in configs if test_filter.lower() in c["name"].lower()]
        if not configs:
            print(f"No tests matching filter: {test_filter}")
            sys.exit(1)
        print(f"Running filtered tests: {[c['name'] for c in configs]}")
    
    all_results = []
    for config in configs:
        result = run_test(config)
        all_results.append(result)
        
        output_file = f"test_outputs/{config['file'].split('/')[-1].replace('.md', '_result.json')}"
        os.makedirs("test_outputs", exist_ok=True)
        
        result_to_save = {k: v for k, v in result.items() if k != "presentation"}
        with open(output_file, 'w') as f:
            json.dump(result_to_save, f, indent=2)
        print(f"Result saved to: {output_file}")
        
        if result.get("presentation"):
            pres_file = f"test_outputs/{config['file'].split('/')[-1].replace('.md', '_presentation.json')}"
            with open(pres_file, 'w') as f:
                json.dump(result["presentation"], f, indent=2)
            print(f"Presentation saved to: {pres_file}")
    
    print_summary(all_results)
    
    if all(r["success"] for r in all_results):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
