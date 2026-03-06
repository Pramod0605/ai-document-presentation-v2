#!/usr/bin/env python3
"""
regenerate_bad_avatars.py

Detects avatar videos that were generated using the fallback reference audio
(reference_audio.wav, ~30 seconds) instead of actual TTS audio, and regenerates
them by calling the HeyGem API (port 5004) with the actual narration text.

Detection heuristic:
  - avatar_status == "completed" AND file exists
  - avatar video duration ≈ 30s (±1.5s tolerance)
  - narration text length > MIN_TEXT_LEN chars
    (short text COULD legitimately be ~30s, so we skip those)

Usage:
  python regenerate_bad_avatars.py [options]

Options:
  --dry-run             Just scan and report, no API calls
  --jobs JOB1 JOB2 ... Limit to specific job IDs
  --avatar-id ID        Avatar library ID to use (default: auto-detect from job)
  --heygem-url URL      HeyGem API URL (default: http://localhost:5004)
  --jobs-dir PATH       Jobs directory (default: player/jobs)
  --tolerance SECS      Duration tolerance in seconds (default: 1.5)
  --min-text-len N      Min text length to flag as bad (default: 100)
  --language LANG       Language for TTS (default: english)
  --speaker SPEAKER     Speaker for Indian languages (default: abhilash)
"""

import os
import sys
import json
import time
import shutil
import argparse
import subprocess
import requests
from typing import Optional
from datetime import datetime
from pathlib import Path

# ─────────────────────────── CONFIG DEFAULTS ────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_JOBS_DIR = os.path.join(SCRIPT_DIR, "player", "jobs")
DEFAULT_HEYGEM_URL = "http://localhost:5004"
REFERENCE_AUDIO_DURATION = 30.0  # seconds
DEFAULT_TOLERANCE = 1.5           # ±1.5s around 30s
DEFAULT_MIN_TEXT_LEN = 100        # skip sections with very short text
POLL_INTERVAL = 10                # seconds between status polls
MAX_POLL_TIME = 1800              # 30 minutes max wait per section
HEYGEM_OUTPUTS_DIR = "/nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox/outputs"


# ─────────────────────────── HELPERS ────────────────────────────────────────

def get_video_duration(path: str) -> Optional[float]:
    """Get video/audio duration via ffprobe. Returns None on error."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             path],
            capture_output=True, text=True, timeout=10
        )
        return float(r.stdout.strip())
    except Exception:
        return None


def is_bad_avatar(video_path: str, text: str,
                  tolerance: float, min_text_len: int) -> tuple:
    """
    Returns (is_bad, duration).
    Bad = duration ≈ 30s AND text is long enough that it shouldn't be 30s.
    """
    if not os.path.exists(video_path):
        return False, None

    duration = get_video_duration(video_path)
    if duration is None:
        return False, None

    near_30s = abs(duration - REFERENCE_AUDIO_DURATION) <= tolerance
    long_enough_text = len(text.strip()) >= min_text_len

    return (near_30s and long_enough_text), duration


def was_section_regenerated(job_dir: str, section_id) -> bool:
    """
    Returns True if regeneration_report.json exists in job_dir AND contains
    a successful entry for section_id.  Returns False if:
      - the report file doesn't exist, OR
      - the report exists but the section is missing / not 'success'.
    """
    report_path = os.path.join(job_dir, "regeneration_report.json")
    if not os.path.exists(report_path):
        return False
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        for sec in report.get("sections", []):
            if str(sec.get("section_id")) == str(section_id):
                return sec.get("result") == "success"
    except Exception:
        pass
    return False


def get_narration_text(section: dict) -> str:
    """Extract full narration text from a section."""
    narration = section.get("narration", "")
    if isinstance(narration, dict):
        return narration.get("full_text", "")
    return str(narration)


def submit_generation(heygem_url: str, text: str, avatar_id: Optional[str],
                      language: str, speaker: str) -> Optional[str]:
    """
    Submit a generation request to HeyGem API.
    Returns task_id on success, None on failure.
    """
    url = f"{heygem_url}/api/generate"
    payload = {"text": text, "language": language}
    if avatar_id:
        payload["avatar_id"] = avatar_id
    if language != "english":
        payload["speaker"] = speaker

    try:
        resp = requests.post(url, data=payload, timeout=60)
        if resp.status_code in (200, 202):
            data = resp.json()
            return data.get("task_id")
        else:
            print(f"    ❌ API error {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"    ❌ Request failed: {e}")
        return None


def poll_until_done(heygem_url: str, task_id: str) -> Optional[dict]:
    """
    Poll /api/status/<task_id> until status is 'completed' or 'failed'.
    Returns final status dict, or None on timeout.
    """
    deadline = time.time() + MAX_POLL_TIME
    while time.time() < deadline:
        try:
            resp = requests.get(f"{heygem_url}/api/status/{task_id}", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status", "unknown")
                progress = data.get("progress", 0)
                print(f"    ⏳ Status: {status} ({progress}%)", end="\r")
                if status == "completed":
                    print()
                    return data
                elif status == "failed":
                    print()
                    print(f"    ❌ Task failed: {data.get('error', 'unknown error')}")
                    return None
        except Exception as e:
            print(f"    ⚠️  Poll error: {e}")
        time.sleep(POLL_INTERVAL)

    print(f"\n    ❌ Timed out waiting for task {task_id}")
    return None


def download_video(task_id: str, dest_path: str) -> bool:
    """
    Copy the generated video from the local HeyGem outputs directory.
    HeyGem saves files as: outputs/final_<task_id>.mp4
    Returns True on success.
    """
    src_path = os.path.join(HEYGEM_OUTPUTS_DIR, f"final_{task_id}.mp4")

    if not os.path.exists(src_path):
        print(f"    ❌ Source file not found: {src_path}")
        return False

    try:
        # Verify source is valid
        dur = get_video_duration(src_path)
        if dur is None or dur < 1.0:
            print(f"    ❌ Source video is invalid (duration={dur})")
            return False

        # Overwrite directly — original is safe in HeyGem outputs/ folder
        shutil.copy2(src_path, dest_path)
        print(f"    ✅ Video copied ({dur:.1f}s) | src: {os.path.basename(src_path)}")
        return True
    except Exception as e:
        print(f"    ❌ Copy error: {e}")
        return False


def save_job_report(job_dir: str, job_id: str, section_results: list):
    """
    Save a per-job regeneration_report.json inside the job directory.
    Called after all sections of a single job are processed.
    """
    success = [r for r in section_results if r.get("result") == "success"]
    failed  = [r for r in section_results if r.get("result") != "success"]

    report = {
        "job_id": job_id,
        "generated_at": datetime.now().isoformat(),
        "total_sections_checked": len(section_results),
        "success": len(success),
        "failed": len(failed),
        "sections": [
            {
                "section_id": r["section_id"],
                "result": r["result"],
                "reason": r.get("reason"),
                "old_duration": r["duration"],
                "new_duration": r.get("new_duration"),
                "new_task_id": r.get("new_task_id"),
                "text_len": r["text_len"],
            }
            for r in section_results
        ]
    }

    report_path = os.path.join(job_dir, "regeneration_report.json")
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"    📄 Job report saved → {report_path}")
    except PermissionError:
        # Fallback: save next to the script
        fallback_path = os.path.join(SCRIPT_DIR, f"regeneration_report_{job_id}.json")
        with open(fallback_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"    📄 Job report saved (fallback) → {fallback_path}")


def update_presentation_json(pres_path: str, section_id, task_id: str,
                             vimeo_url: Optional[str] = None,
                             b2_url: Optional[str] = None):
    """Update presentation.json with new avatar_id, avatar_task_id, vimeo_url, b2_url."""
    try:
        with open(pres_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        updated = False
        for section in data.get("sections", []):
            if str(section.get("section_id")) == str(section_id):
                section["avatar_id"] = task_id
                section["avatar_task_id"] = task_id
                section["avatar_status"] = "completed"
                if vimeo_url:
                    section["vimeo_url"] = vimeo_url
                    section["vimeo_uploaded"] = True
                if b2_url:
                    section["b2_url"] = b2_url
                    section["b2_uploaded"] = True
                updated = True
                break

        if updated:
            with open(pres_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            extras = []
            if vimeo_url: extras.append("vimeo")
            if b2_url: extras.append("b2")
            extra_str = f" + {', '.join(extras)}" if extras else ""
            print(f"    📝 presentation.json updated (section {section_id}{extra_str})")
        else:
            print(f"    ⚠️  Section {section_id} not found in presentation.json")
    except Exception as e:
        print(f"    ⚠️  Failed to update presentation.json: {e}")


# ─────────────────────────── MAIN ───────────────────────────────────────────

def scan_jobs(jobs_dir: str, job_filter: list,
              tolerance: float, min_text_len: int) -> list:
    """
    Scan all jobs and return a list of bad sections.
    Each entry: { job_id, job_dir, section_id, avatar_path, text, duration }
    """
    bad_sections = []
    job_names = sorted(os.listdir(jobs_dir))

    if job_filter:
        job_names = [j for j in job_names if j in job_filter]

    print(f"\n🔍 Scanning {len(job_names)} jobs...")
    for i, job_id in enumerate(job_names):
        job_dir = os.path.join(jobs_dir, job_id)
        pres_path = os.path.join(job_dir, "presentation.json")

        if not os.path.isdir(job_dir) or not os.path.exists(pres_path):
            continue

        try:
            with open(pres_path, "r", encoding="utf-8") as f:
                pres = json.load(f)
        except Exception as e:
            print(f"  ⚠️  [{job_id}] Failed to read presentation.json: {e}")
            continue

        for section in pres.get("sections", []):
            if section.get("avatar_status") != "completed":
                continue

            avatar_rel = section.get("avatar_video", "")
            if not avatar_rel:
                continue

            avatar_path = os.path.join(job_dir, avatar_rel)
            text = get_narration_text(section)
            section_id = section.get("section_id")
            bad, duration = is_bad_avatar(avatar_path, text, tolerance, min_text_len)

            # If already successfully regenerated, skip regardless
            if bad and was_section_regenerated(job_dir, section_id):
                continue

            # Extra check: if video is ~30s but regeneration_report is missing
            # or doesn't record a successful regeneration for this section,
            # flag it regardless of text length.
            if not bad and duration is None:
                # can't determine duration — skip
                pass
            elif not bad:
                # duration was determined; check if it's near 30s but unregenerated
                near_30s = abs(duration - REFERENCE_AUDIO_DURATION) <= tolerance
                if near_30s and not was_section_regenerated(job_dir, section_id):
                    bad = True  # force-flag: 30s video with no successful regen record

            if bad:
                bad_sections.append({
                    "job_id": job_id,
                    "job_dir": job_dir,
                    "pres_path": pres_path,
                    "section_id": section_id,
                    "avatar_path": avatar_path,
                    "avatar_rel": avatar_rel,
                    "text": text,
                    "duration": duration,
                    "text_len": len(text),
                })

        # Progress
        if (i + 1) % 20 == 0:
            print(f"  ... scanned {i+1}/{len(job_names)} jobs, {len(bad_sections)} bad sections found so far")

    return bad_sections


def submit_section(entry: dict, heygem_url: str, avatar_id: Optional[str],
                   language: str, speaker: str) -> dict:
    """Step 1: Submit one section to HeyGem API. Returns entry + task_id."""
    section_id = entry["section_id"]
    text = entry["text"]

    print(f"  � Section {section_id} | {len(text)} chars | {text[:60]}...")

    task_id = submit_generation(heygem_url, text, avatar_id, language, speaker)
    if not task_id:
        print(f"  ❌ Section {section_id}: submission failed")
        return {**entry, "result": "failed", "reason": "submission_failed", "new_task_id": None}

    print(f"  ✅ Section {section_id}: task_id = {task_id}")
    return {**entry, "result": "pending", "new_task_id": task_id}


def process_job_parallel(job_id: str, job_sections: list, heygem_url: str,
                         avatar_id: Optional[str], language: str, speaker: str) -> list:
    """
    Exact same logic as avatar_generator.py submit_parallel_job:
    - Split sections into BATCH_SIZE=3
    - Submit batch → wait for ALL to complete → next batch
    - Each batch gets its own MAX_POLL_TIME timeout (30 min per batch)
    """
    BATCH_SIZE = 3
    batches = [job_sections[i:i+BATCH_SIZE] for i in range(0, len(job_sections), BATCH_SIZE)]
    total_batches = len(batches)
    print(f"\n  📦 {len(job_sections)} sections → {total_batches} batch(es) of {BATCH_SIZE}")

    all_results = []

    for batch_num, batch in enumerate(batches, 1):
        print(f"\n  ─── Batch {batch_num}/{total_batches} ({len(batch)} sections) ───")

        # Step 1: Submit all in this batch
        submitted = []
        for entry in batch:
            result = submit_section(entry, heygem_url, avatar_id, language, speaker)
            submitted.append(result)

        pending = [r for r in submitted if r["result"] == "pending"]
        all_results.extend([r for r in submitted if r["result"] != "pending"])

        if not pending:
            print(f"  ⚠️  All submissions in batch {batch_num} failed.")
            continue

        # Step 2: Poll this batch — each batch gets its OWN full timeout
        print(f"\n  ⏳ Waiting for batch {batch_num} ({len(pending)} tasks)... "
              f"timeout={MAX_POLL_TIME//60} min")

        deadline = time.time() + MAX_POLL_TIME
        remaining = list(pending)

        while remaining and time.time() < deadline:
            still_pending = []
            for entry in remaining:
                task_id = entry["new_task_id"]
                try:
                    resp = requests.get(f"{heygem_url}/api/status/{task_id}", timeout=15)
                    if resp.status_code == 200:
                        data = resp.json()
                        status = data.get("status", "unknown")
                        prog = data.get("progress", 0)

                        if status == "completed":
                            print(f"\n  ✅ Section {entry['section_id']} DONE ({prog}%)")
                            # Extract vimeo_url and b2_url from raw API response
                            # Vimeo/B2 upload is async — wait a bit and re-poll once
                            vimeo_url = data.get("vimeo_url")
                            b2_url = data.get("b2_url")
                            if not vimeo_url or not b2_url:
                                print(f"  ⏳ Waiting 15s for Vimeo/B2 upload to complete...")
                                time.sleep(15)
                                try:
                                    r2 = requests.get(f"{heygem_url}/api/status/{task_id}", timeout=15)
                                    if r2.status_code == 200:
                                        d2 = r2.json()
                                        vimeo_url = vimeo_url or d2.get("vimeo_url")
                                        b2_url = b2_url or d2.get("b2_url")
                                except Exception:
                                    pass
                            success = download_video(task_id, entry["avatar_path"])
                            if success:
                                update_presentation_json(
                                    entry["pres_path"], entry["section_id"], task_id,
                                    vimeo_url=vimeo_url, b2_url=b2_url)
                                new_dur = get_video_duration(entry["avatar_path"])
                                all_results.append({**entry, "result": "success",
                                                    "new_duration": new_dur,
                                                    "vimeo_url": vimeo_url,
                                                    "b2_url": b2_url})
                            else:
                                all_results.append({**entry, "result": "failed",
                                                    "reason": "download_failed"})
                        elif status == "failed":
                            print(f"\n  ❌ Section {entry['section_id']} FAILED: "
                                  f"{data.get('error', '?')}")
                            all_results.append({**entry, "result": "failed",
                                                "reason": f"task_failed: {data.get('error','')}"})
                        else:
                            still_pending.append(entry)
                except Exception as e:
                    print(f"\n  ⚠️  Poll error sec {entry['section_id']}: {e}")
                    still_pending.append(entry)

            remaining = still_pending
            if remaining:
                secs = ", ".join(str(e["section_id"]) for e in remaining)
                print(f"  ⏳ Batch {batch_num} waiting [{secs}]...", end="\r")
                time.sleep(POLL_INTERVAL)

        # Timeout
        for entry in remaining:
            print(f"\n  ❌ Section {entry['section_id']} timed out (batch {batch_num})")
            all_results.append({**entry, "result": "failed", "reason": "timeout"})

        batch_ok = sum(1 for r in all_results if r.get("result") == "success"
                       and r["section_id"] in [e["section_id"] for e in batch])
        print(f"\n  ✔️  Batch {batch_num} complete: {batch_ok}/{len(batch)} succeeded")

    return all_results





def main():
    parser = argparse.ArgumentParser(description="Detect and fix bad avatar videos")
    parser.add_argument("--dry-run", action="store_true",
                        help="Just scan and report, no API calls")
    parser.add_argument("--jobs", nargs="*", default=[],
                        help="Limit to specific job IDs")
    parser.add_argument("--avatar-id", default=None,
                        help="Avatar library ID to use (e.g. avatar_42a369f1). "
                             "If not set, uses the avatar_id already in the section.")
    parser.add_argument("--heygem-url", default=DEFAULT_HEYGEM_URL,
                        help=f"HeyGem API URL (default: {DEFAULT_HEYGEM_URL})")
    parser.add_argument("--jobs-dir", default=DEFAULT_JOBS_DIR,
                        help="Jobs directory path")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE,
                        help=f"Duration tolerance in seconds (default: {DEFAULT_TOLERANCE})")
    parser.add_argument("--min-text-len", type=int, default=DEFAULT_MIN_TEXT_LEN,
                        help=f"Min narration text length to flag (default: {DEFAULT_MIN_TEXT_LEN})")
    parser.add_argument("--language", default="english",
                        help="TTS language (default: english)")
    parser.add_argument("--speaker", default="abhilash",
                        help="TTS speaker for Indian languages (default: abhilash)")

    args = parser.parse_args()

    print("=" * 70)
    print("🛠️  Avatar Regeneration Script")
    print("=" * 70)
    print(f"  Jobs dir:    {args.jobs_dir}")
    print(f"  HeyGem URL:  {args.heygem_url}")
    print(f"  Avatar ID:   {args.avatar_id or '(auto from section)'}")
    print(f"  Tolerance:   ±{args.tolerance}s around {REFERENCE_AUDIO_DURATION}s")
    print(f"  Min text:    {args.min_text_len} chars")
    print(f"  Language:    {args.language}")
    print(f"  Dry run:     {args.dry_run}")
    if args.jobs:
        print(f"  Job filter:  {args.jobs}")

    # Step 1: Scan
    bad_sections = scan_jobs(
        args.jobs_dir,
        args.jobs,
        args.tolerance,
        args.min_text_len
    )

    print(f"\n{'=' * 70}")
    print(f"📊 Scan complete: {len(bad_sections)} bad sections found")
    print("=" * 70)

    if not bad_sections:
        print("✅ Nothing to do!")
        return

    # Group by job for display
    by_job = {}
    for entry in bad_sections:
        by_job.setdefault(entry["job_id"], []).append(entry)

    print(f"\nAffected jobs: {len(by_job)}")
    for job_id, sections in list(by_job.items())[:10]:
        print(f"  {job_id}: {len(sections)} section(s)")
    if len(by_job) > 10:
        print(f"  ... and {len(by_job) - 10} more jobs")

    if args.dry_run:
        print("\n⚠️  DRY RUN — no changes made. Remove --dry-run to regenerate.")

        # Save per-job dry-run reports inside each job folder
        by_job_dry = {}
        for entry in bad_sections:
            by_job_dry.setdefault(entry["job_id"], []).append(entry)

        for job_id, job_entries in by_job_dry.items():
            dry_results = [
                {
                    "section_id": e["section_id"],
                    "result": "dry_run",
                    "reason": "not_run",
                    "old_duration": e["duration"],
                    "new_duration": None,
                    "new_task_id": None,
                    "text_len": e["text_len"],
                }
                for e in job_entries
            ]
            save_job_report(job_entries[0]["job_dir"], job_id, dry_results)

        # Save global dry-run report
        report_path = os.path.join(SCRIPT_DIR, "regeneration_report_dryrun.json")
        with open(report_path, "w") as f:
            clean = [{k: v for k, v in e.items()} for e in bad_sections]
            json.dump({"total": len(bad_sections), "sections": clean}, f, indent=2)
        print(f"📄 Global dry run report saved: {report_path}")
        return

    # Step 2: Confirm before proceeding (unless piped / non-interactive)
    if sys.stdin.isatty():
        print(f"\n⚠️  About to regenerate {len(bad_sections)} avatar videos.")
        answer = input("   Continue? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    # Step 3: Process
    results = []
    success_count = 0
    fail_count = 0
    start_time = time.time()

    # Group bad sections by job so we can save per-job reports
    by_job = {}
    for entry in bad_sections:
        by_job.setdefault(entry["job_id"], []).append(entry)

    global_idx = 0
    for job_id, job_sections in by_job.items():
        print(f"\n{'─'*70}")
        print(f"📁 Job: {job_id} ({len(job_sections)} section(s) to fix)")

        # Resolve avatar_id once for the whole job
        avatar_id = args.avatar_id
        if not avatar_id:
            try:
                with open(job_sections[0]["pres_path"], "r") as f:
                    pres = json.load(f)
                for sec in pres.get("sections", []):
                    stored_id = sec.get("avatar_id", "")
                    if stored_id and stored_id.startswith("avatar_"):
                        avatar_id = stored_id
                        break
            except Exception:
                pass
        print(f"   Avatar: {avatar_id or 'default'}")

        # Submit ALL sections in parallel, poll together
        job_results = process_job_parallel(
            job_id, job_sections, args.heygem_url,
            avatar_id, args.language, args.speaker
        )

        for r in job_results:
            global_idx += 1
            if r["result"] == "success":
                success_count += 1
            else:
                fail_count += 1
        results.extend(job_results)

        # Save per-job report after each job finishes
        save_job_report(job_sections[0]["job_dir"], job_id, job_results)

        # Save/update global incremental report
        report_path = os.path.join(SCRIPT_DIR, "regeneration_report.json")
        with open(report_path, "w") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total": len(bad_sections),
                "processed": global_idx,
                "success": success_count,
                "failed": fail_count,
                "elapsed_minutes": round((time.time() - start_time) / 60, 1),
                "results": results
            }, f, indent=2, default=str)

    # Final summary
    elapsed = (time.time() - start_time) / 60
    print(f"\n{'=' * 70}")
    print(f"🎉 Done! {success_count} regenerated, {fail_count} failed")
    print(f"   Total time: {elapsed:.1f} minutes")
    print(f"   Report: {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
