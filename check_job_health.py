#!/usr/bin/env python3
"""
Job Health Checker - Comprehensive Report Generator for V2.5 Pipeline Jobs

Usage:
    python check_job_health.py <job_id>
    python check_job_health.py              # Checks most recent job
    python check_job_health.py --all        # Lists all jobs with status

Checks:
    1. Job file existence (presentation.json, audio/, videos/)
    2. Content structure (sections, segments, Section Bible compliance)
    3. Audio generation status (TTS success rate)
    4. Video generation status (Manim/WAN success rate)
    5. Analytics & Certification reports
    6. Overall health score

Output: Produces a detailed console report and optionally saves to file.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, Any, List, Optional

# Default paths
JOBS_DIR = Path("player/jobs")
JOBS_INDEX = JOBS_DIR / "jobs_index.json"


def load_jobs_index() -> Dict[str, Any]:
    """Load the jobs index file."""
    if JOBS_INDEX.exists():
        try:
            with open(JOBS_INDEX, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load jobs_index.json: {e}")
            return {}
    return {}


def get_most_recent_job() -> Optional[str]:
    """Get the most recently created job ID."""
    jobs = load_jobs_index()
    if not jobs:
        return None
    
    sorted_jobs = sorted(
        jobs.items(),
        key=lambda x: x[1].get("created_at", x[1].get("created", "")),
        reverse=True
    )
    return sorted_jobs[0][0] if sorted_jobs else None


def list_all_jobs() -> None:
    """Print a summary of all jobs."""
    jobs = load_jobs_index()
    
    if not jobs:
        print("❌ No jobs found in jobs_index.json")
        return
    
    # Sort by date, newest first
    sorted_jobs = sorted(
        jobs.items(),
        key=lambda x: x[1].get("created_at", x[1].get("created", "")),
        reverse=True
    )
    
    print("=" * 70)
    print(f"{'JOB ID':10} | {'STATUS':22} | {'CREATED'}")
    print("-" * 70)
    
    status_counts = {}
    for job_id, job in sorted_jobs[:50]:  # Show last 50 jobs
        status = job.get("status", "unknown")
        created = job.get("created_at", job.get("created", "N/A"))[:19]
        
        # Emoji for status
        emoji = {
            "completed": "✅",
            "completed_with_errors": "⚠️",
            "failed": "❌",
            "processing": "🔄",
            "queued": "⏳"
        }.get(status, "❓")
        
        print(f"{job_id:10} | {emoji} {status:19} | {created}")
        
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("-" * 70)
    print(f"Total: {len(jobs)} jobs")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")


def check_job_health(job_id: str) -> Dict[str, Any]:
    """
    Perform comprehensive health check on a job.
    
    Returns a dict with health metrics and issues.
    """
    job_dir = JOBS_DIR / job_id
    results = {
        "job_id": job_id,
        "timestamp": datetime.now().isoformat(),
        "exists": False,
        "files": {},
        "content": {},
        "audio": {},
        "video": {},
        "analytics": {},
        "certification": {},
        "errors": [],
        "warnings": [],
        "score": 0,
        "max_score": 100
    }
    
    # 1. EXISTENCE CHECKS
    if not job_dir.exists():
        results["errors"].append(f"Job directory not found: {job_dir}")
        return results
    
    results["exists"] = True
    
    # Check required files
    required_files = {
        "presentation.json": job_dir / "presentation.json",
        "source_markdown.md": job_dir / "source_markdown.md",
        "index.html": job_dir / "index.html"
    }
    
    optional_files = {
        "certification_report.txt": job_dir / "certification_report.txt",
        "analytics.json": job_dir / "analytics.json",
        "render_prompts.json": job_dir / "render_prompts.json",
        "avatar_status.json": job_dir / "avatar_status.json"
    }
    
    for name, path in required_files.items():
        if path.exists():
            results["files"][name] = {"exists": True, "size": path.stat().st_size}
            results["score"] += 10
        else:
            results["files"][name] = {"exists": False}
            results["errors"].append(f"Missing required file: {name}")
    
    for name, path in optional_files.items():
        if path.exists():
            results["files"][name] = {"exists": True, "size": path.stat().st_size}
            results["score"] += 2
        else:
            results["files"][name] = {"exists": False}
            results["warnings"].append(f"Missing optional file: {name}")
    
    # Check directories
    audio_dir = job_dir / "audio"
    videos_dir = job_dir / "videos"
    images_dir = job_dir / "images"
    
    results["files"]["audio/"] = {"exists": audio_dir.exists()}
    results["files"]["videos/"] = {"exists": videos_dir.exists()}
    results["files"]["images/"] = {"exists": images_dir.exists()}
    
    # 2. LOAD PRESENTATION.JSON
    pres_path = job_dir / "presentation.json"
    if not pres_path.exists():
        return results
    
    try:
        with open(pres_path, "r", encoding="utf-8") as f:
            presentation = json.load(f)
    except json.JSONDecodeError as e:
        results["errors"].append(f"Invalid JSON in presentation.json: {e}")
        return results
    
    # 3. CONTENT ANALYSIS
    sections = presentation.get("sections", [])
    results["content"]["total_sections"] = len(sections)
    
    if len(sections) == 0:
        results["errors"].append("No sections found in presentation.json")
        return results
    
    # Section Bible Compliance
    section_types = {}
    for sec in sections:
        st = sec.get("section_type", "unknown")
        section_types[st] = section_types.get(st, 0) + 1
    
    results["content"]["section_types"] = section_types
    
    # Required sections (V2.5 Bible)
    required_types = ["intro", "summary", "memory", "recap"]
    for rt in required_types:
        if rt in section_types:
            results["score"] += 5
        else:
            results["errors"].append(f"Missing required section type: {rt}")
    
    # Content section count
    content_count = section_types.get("content", 0) + section_types.get("example", 0)
    results["content"]["content_sections"] = content_count
    
    if content_count >= 1:
        results["score"] += 10
    else:
        results["errors"].append("No content/example sections found")
    
    # Total segments
    total_segments = 0
    for sec in sections:
        narration = sec.get("narration", {})
        segments = narration.get("segments", [])
        total_segments += len(segments)
    
    results["content"]["total_segments"] = total_segments
    
    # 4. AUDIO ANALYSIS
    if audio_dir.exists():
        audio_files = list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.wav"))
        non_empty = [f for f in audio_files if f.stat().st_size > 1000]
        
        results["audio"]["total_files"] = len(audio_files)
        results["audio"]["valid_files"] = len(non_empty)
        results["audio"]["empty_files"] = len(audio_files) - len(non_empty)
        
        # Check section-level audio wiring
        wired = 0
        for sec in sections:
            if sec.get("audio_path"):
                audio_abs = job_dir / sec["audio_path"]
                if audio_abs.exists() and audio_abs.stat().st_size > 1000:
                    wired += 1
        
        results["audio"]["wired_sections"] = wired
        results["audio"]["total_sections"] = len(sections)
        
        audio_ratio = wired / len(sections) if sections else 0
        results["score"] += int(audio_ratio * 15)
        
        if wired < len(sections):
            results["warnings"].append(f"Audio wiring incomplete: {wired}/{len(sections)} sections")
    else:
        results["audio"]["total_files"] = 0
        results["errors"].append("No audio directory found")
    
    # 5. VIDEO ANALYSIS
    if videos_dir.exists():
        video_files = list(videos_dir.glob("*.mp4"))
        non_empty = [f for f in video_files if f.stat().st_size > 5000]
        
        results["video"]["total_files"] = len(video_files)
        results["video"]["valid_files"] = len(non_empty)
        
        # Check renderer assignments
        manim_sections = 0
        video_sections = 0
        for sec in sections:
            renderer = sec.get("renderer", sec.get("derived_renderer", "none"))
            if renderer == "manim":
                manim_sections += 1
            elif renderer in ("wan_video", "wan", "video"):
                video_sections += 1
        
        results["video"]["manim_sections"] = manim_sections
        results["video"]["video_sections"] = video_sections
        
        if len(non_empty) > 0:
            results["score"] += 15
    else:
        results["video"]["total_files"] = 0
        results["warnings"].append("No videos directory found")
    
    # 6. ANALYTICS
    analytics_path = job_dir / "analytics.json"
    if analytics_path.exists():
        try:
            with open(analytics_path, "r", encoding="utf-8") as f:
                analytics = json.load(f)
            results["analytics"]["exists"] = True
            results["analytics"]["status"] = analytics.get("status", "unknown")
            results["analytics"]["total_cost"] = analytics.get("total_cost_usd", 0)
            results["score"] += 5
        except:
            results["analytics"]["exists"] = False
            results["warnings"].append("Analytics file exists but is unreadable")
    else:
        results["analytics"]["exists"] = False
        results["warnings"].append("Analytics not generated (missing analytics.json)")
    
    # 7. CERTIFICATION REPORT
    cert_path = job_dir / "certification_report.txt"
    if cert_path.exists():
        try:
            with open(cert_path, "r", encoding="utf-8") as f:
                cert_content = f.read()
            results["certification"]["exists"] = True
            
            # Parse key metrics from cert report
            if "✅" in cert_content:
                results["certification"]["has_passes"] = True
                results["score"] += 5
            if "❌" in cert_content:
                results["certification"]["has_failures"] = True
                results["warnings"].append("Certification report has failures")
            if "TTS Duration Check: ✅ PASS" in cert_content:
                results["certification"]["tts_pass"] = True
                results["score"] += 5
        except:
            results["certification"]["exists"] = False
    else:
        results["certification"]["exists"] = False
    
    # 8. JOBS INDEX STATUS
    jobs_index = load_jobs_index()
    if job_id in jobs_index:
        job_info = jobs_index[job_id]
        results["index_status"] = job_info.get("status", "unknown")
        results["created"] = job_info.get("created_at", job_info.get("created", "N/A"))
        
        if job_info.get("error"):
            results["index_error"] = job_info["error"][:200]
    
    return results


def print_health_report(results: Dict[str, Any]) -> None:
    """Print a formatted health report."""
    print()
    print("=" * 70)
    print(f"   🔍 JOB HEALTH REPORT: {results['job_id']}")
    print("=" * 70)
    
    if not results["exists"]:
        print(f"❌ Job directory not found!")
        return
    
    # Status from index
    if "index_status" in results:
        status_emoji = {
            "completed": "✅",
            "completed_with_errors": "⚠️",
            "failed": "❌",
            "processing": "🔄",
            "queued": "⏳"
        }.get(results["index_status"], "❓")
        print(f"\n📊 Index Status: {status_emoji} {results['index_status']}")
        if results.get("created"):
            print(f"   Created: {results['created']}")
    
    # Files
    print(f"\n📁 FILES")
    print("-" * 40)
    for name, info in results["files"].items():
        icon = "✅" if info.get("exists") else "❌"
        size = f"({info.get('size', 0):,} bytes)" if info.get("size") else ""
        print(f"   {icon} {name} {size}")
    
    # Content
    print(f"\n📖 CONTENT STRUCTURE")
    print("-" * 40)
    content = results["content"]
    print(f"   Total Sections: {content.get('total_sections', 0)}")
    print(f"   Total Segments: {content.get('total_segments', 0)}")
    print(f"   Section Types:")
    for st, count in content.get("section_types", {}).items():
        print(f"      • {st}: {count}")
    
    # Audio
    print(f"\n🔊 AUDIO STATUS")
    print("-" * 40)
    audio = results["audio"]
    print(f"   Files Generated: {audio.get('valid_files', 0)}/{audio.get('total_files', 0)}")
    print(f"   Sections Wired:  {audio.get('wired_sections', 0)}/{audio.get('total_sections', 0)}")
    
    # Video
    print(f"\n🎬 VIDEO STATUS")
    print("-" * 40)
    video = results["video"]
    print(f"   Videos Generated: {video.get('valid_files', 0)}/{video.get('total_files', 0)}")
    print(f"   Manim Sections:   {video.get('manim_sections', 0)}")
    print(f"   WAN Sections:     {video.get('video_sections', 0)}")
    
    # Analytics
    print(f"\n📈 ANALYTICS")
    print("-" * 40)
    analytics = results["analytics"]
    if analytics.get("exists"):
        print(f"   ✅ Analytics generated")
        print(f"   Status: {analytics.get('status', 'N/A')}")
        if analytics.get("total_cost"):
            print(f"   Cost: ${analytics['total_cost']:.4f}")
    else:
        print(f"   ❌ Analytics NOT generated")
    
    # Certification
    print(f"\n📋 CERTIFICATION")
    print("-" * 40)
    cert = results["certification"]
    if cert.get("exists"):
        print(f"   ✅ Certification report generated")
        if cert.get("tts_pass"):
            print(f"   ✅ TTS Duration Check: PASS")
        if cert.get("has_failures"):
            print(f"   ⚠️  Report contains failures")
    else:
        print(f"   ❌ No certification report")
    
    # Errors and Warnings
    if results["errors"]:
        print(f"\n❌ ERRORS ({len(results['errors'])})")
        print("-" * 40)
        for err in results["errors"]:
            print(f"   • {err}")
    
    if results["warnings"]:
        print(f"\n⚠️  WARNINGS ({len(results['warnings'])})")
        print("-" * 40)
        for warn in results["warnings"]:
            print(f"   • {warn}")
    
    if "index_error" in results:
        print(f"\n💥 JOB ERROR")
        print("-" * 40)
        print(f"   {results['index_error']}")
    
    # Health Score
    print()
    print("=" * 70)
    score = results["score"]
    max_score = results["max_score"]
    pct = (score / max_score) * 100
    
    if pct >= 80:
        grade = "🟢 HEALTHY"
    elif pct >= 60:
        grade = "🟡 FAIR"
    elif pct >= 40:
        grade = "🟠 DEGRADED"
    else:
        grade = "🔴 CRITICAL"
    
    print(f"   HEALTH SCORE: {score}/{max_score} ({pct:.0f}%) - {grade}")
    print("=" * 70)


def main():
    if len(sys.argv) < 2:
        # Default: check most recent job
        job_id = get_most_recent_job()
        if not job_id:
            print("❌ No jobs found. Specify a job ID or run with --all")
            sys.exit(1)
        print(f"ℹ️  Checking most recent job: {job_id}")
    elif sys.argv[1] == "--all":
        list_all_jobs()
        sys.exit(0)
    elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
        print(__doc__)
        sys.exit(0)
    else:
        job_id = sys.argv[1]
    
    results = check_job_health(job_id)
    print_health_report(results)
    
    # Optionally save report
    if "--save" in sys.argv:
        report_path = JOBS_DIR / job_id / "health_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📄 Report saved to: {report_path}")


if __name__ == "__main__":
    main()
