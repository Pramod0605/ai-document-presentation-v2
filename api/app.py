import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS

from core.pipeline import process_pdf_to_videos
from core.pipeline_v12 import process_markdown_to_videos_v12 as process_markdown_to_videos
from core.pipeline_v14 import process_markdown_to_presentation_v14, get_pipeline_info, validate_presentation_v14
from core.job_manager import job_manager, run_job_async, is_job_running, get_current_job_id

app = Flask(__name__)
CORS(app)

PLAYER_DIR = Path(__file__).parent.parent / "player"
ASSETS_DIR = PLAYER_DIR / "assets"
JOBS_DIR = PLAYER_DIR / "jobs"
TEMP_DIR = Path(tempfile.gettempdir()) / "ai_education_jobs"

os.makedirs(ASSETS_DIR / "videos", exist_ok=True)
os.makedirs(ASSETS_DIR / "audio", exist_ok=True)
os.makedirs(JOBS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

def setup_job_folder(job_output_dir: Path):
    """Copy player files to job folder for self-contained playback"""
    os.makedirs(job_output_dir / "videos", exist_ok=True)
    os.makedirs(job_output_dir / "audio", exist_ok=True)
    # Copy player files for self-contained job
    for filename in ["index.html", "player.js"]:
        src = PLAYER_DIR / filename
        dst = job_output_dir / filename
        if src.exists() and not dst.exists():
            shutil.copy(str(src), str(dst))

@app.route("/")
def index():
    return redirect("/dashboard")

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "ai-animated-education-phase1",
        "version": "1.4.0",
        "features": ["job_mode", "pdf", "markdown", "v14_pipeline", "split_director"]
    })


@app.route("/submit_job", methods=["POST"])
def submit_job():
    try:
        if is_job_running():
            current_id = get_current_job_id()
            return jsonify({
                "status": "busy",
                "message": "A job is already running. Please wait for it to complete.",
                "current_job_id": current_id
            }), 409
        
        subject = request.form.get("subject", "General Science")
        grade = request.form.get("grade", "9")
        dry_run = request.form.get("dry_run", "false").lower() == "true"
        skip_wan = request.form.get("skip_wan", "false").lower() == "true"
        skip_avatar = request.form.get("skip_avatar", "false").lower() == "true"
        tts_provider = request.form.get("tts_provider", "narakeet")
        
        if "file" in request.files:
            uploaded_file = request.files["file"]
            if uploaded_file.filename == "":
                return jsonify({"error": "No file selected"}), 400
            
            filename = (uploaded_file.filename or "").lower()
            
            if filename.endswith(".pdf"):
                job_type = "pdf"
                suffix = ".pdf"
            elif filename.endswith(".md") or filename.endswith(".markdown") or filename.endswith(".txt"):
                job_type = "markdown_file"
                suffix = ".md"
            else:
                return jsonify({"error": "Unsupported file type. Please upload PDF or Markdown (.md) file"}), 400
            
            temp_file = TEMP_DIR / f"{os.urandom(8).hex()}{suffix}"
            uploaded_file.save(str(temp_file))
            original_filename = uploaded_file.filename
            
            job_id = job_manager.create_job("v14_pipeline", {
                "subject": subject,
                "grade": grade,
                "file_path": str(temp_file),
                "source_file": original_filename,
                "skip_wan": skip_wan,
                "skip_avatar": skip_avatar,
                "tts_provider": tts_provider
            })
            
            job_output_dir = JOBS_DIR / job_id
            setup_job_folder(job_output_dir)
            
            if job_type == "pdf":
                run_job_async(
                    job_id,
                    process_pdf_job,
                    pdf_path=str(temp_file),
                    subject=subject,
                    grade=grade,
                    output_dir=str(job_output_dir),
                    dry_run=dry_run,
                    skip_wan=skip_wan,
                    skip_avatar=skip_avatar,
                    source_file=original_filename
                )
            else:
                with open(temp_file, "r", encoding="utf-8") as f:
                    markdown_content = f.read()
                os.unlink(temp_file)
                
                content_preview = markdown_content[:300].replace('\n', ' ').strip()
                if len(markdown_content) > 300:
                    content_preview += "..."
                
                job_manager.update_job(job_id, {"content_preview": content_preview}, persist=True)
                
                run_job_async(
                    job_id,
                    process_markdown_job,
                    markdown_content=markdown_content,
                    subject=subject,
                    grade=grade,
                    output_dir=str(job_output_dir),
                    dry_run=dry_run,
                    skip_wan=skip_wan,
                    skip_avatar=skip_avatar,
                    source_file=original_filename,
                    tts_provider=tts_provider
                )
        
        elif request.is_json:
            data = request.json
            markdown_content = data.get("markdown", "")
            subject = data.get("subject", subject)
            grade = data.get("grade", grade)
            dry_run = data.get("dry_run", False)
            skip_wan = data.get("skip_wan", False)
            skip_avatar = data.get("skip_avatar", False)
            tts_provider = data.get("tts_provider", "narakeet")
            
            if not markdown_content:
                return jsonify({"error": "Markdown content is required"}), 400
            
            content_preview = markdown_content[:300].replace('\n', ' ').strip()
            if len(markdown_content) > 300:
                content_preview += "..."
            
            job_id = job_manager.create_job("v14_pipeline", {
                "subject": subject,
                "grade": grade,
                "dry_run": dry_run,
                "skip_wan": skip_wan,
                "skip_avatar": skip_avatar,
                "tts_provider": tts_provider,
                "content_preview": content_preview
            })
            
            job_output_dir = JOBS_DIR / job_id
            setup_job_folder(job_output_dir)
            
            run_job_async(
                job_id,
                process_markdown_job,
                markdown_content=markdown_content,
                subject=subject,
                grade=grade,
                output_dir=str(job_output_dir),
                dry_run=dry_run,
                skip_wan=skip_wan,
                skip_avatar=skip_avatar,
                tts_provider=tts_provider
            )
        
        else:
            return jsonify({"error": "Please provide a file or markdown content"}), 400
        
        mode_msg = " (DRY RUN - prompts only, no real rendering)" if dry_run else ""
        job_data = job_manager.get_job(job_id)
        content_preview = None
        if job_data:
            content_preview = job_data.get("content_preview") or job_data.get("params", {}).get("content_preview")
        
        return jsonify({
            "status": "accepted",
            "job_id": job_id,
            "dry_run": dry_run,
            "skip_wan": skip_wan,
            "skip_avatar": skip_avatar,
            "content_preview": content_preview,
            "message": f"Job submitted successfully{mode_msg}. Poll /job/<job_id>/status for progress."
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route("/job/<job_id>/status", methods=["GET"])
def get_job_status(job_id):
    job = job_manager.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    response = {
        "job_id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "current_step": job["current_step_name"],
        "current_phase": job.get("current_phase_key"),
        "status_message": job.get("status_message"),
        "steps_completed": job["steps_completed"],
        "total_steps": job["total_steps"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "completed_at": job["completed_at"],
        "error": job["error"]
    }
    
    if job["status"] == "failed":
        response["failure_message"] = job.get("failure_message")
        response["failed_phase"] = job.get("failed_phase")
    
    return jsonify(response)


@app.route("/jobs", methods=["GET"])
def list_all_jobs():
    """List all jobs with their status (persisted across restarts)."""
    jobs = job_manager.get_all_jobs()
    return jsonify({
        "jobs": [{
            "job_id": j["id"],
            "type": j.get("type", "unknown"),
            "status": j["status"],
            "progress": j["progress"],
            "created_at": j["created_at"],
            "completed_at": j["completed_at"],
            "error": j.get("error"),
            "params": {
                "subject": j.get("params", {}).get("subject", ""),
                "grade": j.get("params", {}).get("grade", ""),
                "dry_run": j.get("params", {}).get("dry_run", False)
            }
        } for j in jobs],
        "total": len(jobs)
    })


def process_pdf_job(job_id: str, pdf_path: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None) -> dict:
    try:
        result = process_pdf_to_videos(
            pdf_path=pdf_path,
            subject=subject,
            grade=grade,
            output_dir=output_dir,
            job_id=job_id,
            dry_run=dry_run,
            skip_wan=skip_wan,
            skip_avatar=skip_avatar,
            source_file=source_file
        )
        return result
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


def process_markdown_job(job_id: str, markdown_content: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None, tts_provider: str = "narakeet") -> dict:
    """Process markdown using V1.4 Split Director pipeline."""
    job_output_dir = Path(output_dir)
    
    def status_callback(jid, phase, message):
        job_manager.update_job(jid, {
            "current_phase_key": phase,
            "status_message": message
        }, persist=True)
    
    generate_tts = tts_provider != "estimate" and not dry_run
    effective_tts = "pyttsx3" if dry_run else tts_provider
    
    presentation, tracker = process_markdown_to_presentation_v14(
        markdown_content=markdown_content,
        subject=subject,
        grade=grade,
        job_id=job_id,
        update_status_callback=status_callback,
        generate_tts=generate_tts,
        output_dir=job_output_dir,
        tts_provider=effective_tts
    )
    
    validation = validate_presentation_v14(presentation)
    
    pres_path = job_output_dir / "presentation.json"
    with open(pres_path, "w") as f:
        json.dump(presentation, f, indent=2)
    
    analytics_summary = tracker.get_summary() if hasattr(tracker, 'get_summary') else {}
    
    job_manager.update_job(job_id, {
        "status": "completed" if not validation.get("has_errors") else "failed",
        "progress": 100,
        "validation": validation,
        "analytics": analytics_summary
    }, persist=True)
    
    return {
        "status": "success" if not validation.get("has_errors") else "validation_failed",
        "job_id": job_id,
        "validation": validation,
        "analytics": analytics_summary,
        "output_path": str(pres_path),
        "skip_wan": skip_wan,
        "tts_provider": effective_tts,
        "pipeline_version": "v1.4"
    }


@app.route("/process_pdf", methods=["POST"])
def process_pdf():
    """Legacy endpoint - now creates job folders for proper isolation."""
    try:
        subject = request.form.get("subject", "General Science")
        grade = request.form.get("grade", "9")
        
        if "file" in request.files:
            pdf_file = request.files["file"]
            if pdf_file.filename == "":
                return jsonify({"error": "No file selected"}), 400
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf_file.save(tmp.name)
                tmp_path = tmp.name
            
            job_id = job_manager.create_job("pdf_legacy", {
                "subject": subject,
                "grade": grade,
                "source_file": pdf_file.filename
            })
            job_output_dir = JOBS_DIR / job_id
            setup_job_folder(job_output_dir)
            
            try:
                result = process_pdf_to_videos(
                    pdf_path=tmp_path,
                    subject=subject,
                    grade=grade,
                    output_dir=str(job_output_dir),
                    job_id=job_id
                )
                result["job_id"] = job_id
            finally:
                os.unlink(tmp_path)
        
        elif request.is_json and "markdown" in request.json:
            markdown_content = request.json["markdown"]
            subject = request.json.get("subject", subject)
            grade = request.json.get("grade", grade)
            
            job_id = job_manager.create_job("markdown_legacy", {
                "subject": subject,
                "grade": grade
            })
            job_output_dir = JOBS_DIR / job_id
            setup_job_folder(job_output_dir)
            
            result = process_markdown_to_videos(
                markdown_content=markdown_content,
                subject=subject,
                grade=grade,
                output_dir=str(job_output_dir),
                job_id=job_id
            )
            result["job_id"] = job_id
        
        else:
            return jsonify({
                "error": "Please provide either a PDF file or markdown content"
            }), 400
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route("/process_markdown", methods=["POST"])
def process_markdown():
    """Legacy endpoint - now creates job folders for proper isolation."""
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.json
        markdown_content = data.get("markdown", "")
        subject = data.get("subject", "General Science")
        grade = data.get("grade", "9")
        
        if not markdown_content:
            return jsonify({"error": "Markdown content is required"}), 400
        
        job_id = job_manager.create_job("markdown_legacy", {
            "subject": subject,
            "grade": grade
        })
        job_output_dir = JOBS_DIR / job_id
        setup_job_folder(job_output_dir)
        
        result = process_markdown_to_videos(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            output_dir=str(job_output_dir),
            job_id=job_id
        )
        result["job_id"] = job_id
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route("/jobs/<job_id>/resume", methods=["POST"])
def resume_job(job_id):
    """Resume a failed job from a specific phase.
    
    POST body:
    - from_phase: "render" or "audio" (default: "audio")
    - dry_run: boolean (default: false)
    - skip_wan: boolean (default: false)
    - skip_avatar: boolean (default: false)
    """
    from core.pipeline_v12 import resume_job_from_phase, detect_job_phase
    
    data = request.get_json() or {}
    from_phase = data.get("from_phase", "audio")
    dry_run = data.get("dry_run", False)
    skip_wan = data.get("skip_wan", False)
    skip_avatar = data.get("skip_avatar", False)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    phases = detect_job_phase(str(job_dir))
    
    if not phases["presentation"]:
        return jsonify({
            "error": "Cannot resume - presentation.json missing. Job must have completed Director phase.",
            "job_id": job_id,
            "phases": phases
        }), 400
    
    try:
        print(f"[API] Resuming job {job_id} from phase: {from_phase}")
        result = resume_job_from_phase(
            job_id=job_id,
            from_phase=from_phase,
            dry_run=dry_run,
            skip_wan=skip_wan,
            skip_avatar=skip_avatar
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "job_id": job_id
        }), 500


@app.route("/jobs/<job_id>/phases", methods=["GET"])
def get_job_phases(job_id):
    """Get phase completion status for a job."""
    from core.pipeline_v12 import detect_job_phase
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    phases = detect_job_phase(str(job_dir))
    phases["job_id"] = job_id
    
    return jsonify(phases)


@app.route("/jobs/<job_id>/rerender", methods=["POST"])
def rerender_job_sections(job_id):
    """Re-render specific sections with WAN video renderer.
    
    POST body:
    - section_ids: List of section IDs to re-render (required)
    - renderer: "wan_video" (default, only option currently)
    """
    from core.llm_client_v12 import rerender_sections_wan
    from core.analytics import create_tracker
    
    data = request.get_json() or {}
    section_ids = data.get("section_ids", [])
    
    if not section_ids:
        return jsonify({"error": "section_ids required"}), 400
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    pres_path = job_dir / "presentation.json"
    if not pres_path.exists():
        return jsonify({"error": "presentation.json not found"}), 400
    
    try:
        with open(pres_path, "r") as f:
            presentation = json.load(f)
        
        tracker = create_tracker(job_id)
        
        print(f"[API] Re-rendering sections {section_ids} for job {job_id}")
        updated = rerender_sections_wan(presentation, section_ids, tracker)
        
        with open(pres_path, "w") as f:
            json.dump(updated, f, indent=2)
        
        sections_updated = []
        for s in updated.get("sections", []):
            sid = s.get("section_id") or s.get("id")
            if sid in section_ids:
                sections_updated.append({
                    "section_id": sid,
                    "renderer": s.get("renderer"),
                    "video_prompts_count": len(s.get("video_prompts", [])),
                    "error": s.get("renderer_error")
                })
        
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "sections_updated": sections_updated
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "job_id": job_id
        }), 500


@app.route("/jobs/<job_id>/generate_videos", methods=["POST"])
def generate_videos_from_prompts(job_id):
    """Generate actual videos from video_prompts using WAN/KIE API.
    
    POST body:
    - section_ids: List of section IDs to generate videos for (required)
    - skip_wan: If true, create placeholder videos (default: false)
    - dry_run: If true, only create marker files (default: false)
    """
    from render.wan.wan_runner import render_from_video_prompts, WanRenderError
    
    data = request.get_json() or {}
    section_ids = data.get("section_ids", [])
    skip_wan = data.get("skip_wan", False)
    dry_run = data.get("dry_run", False)
    
    if not section_ids:
        return jsonify({"error": "section_ids required"}), 400
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    pres_path = job_dir / "presentation.json"
    if not pres_path.exists():
        return jsonify({"error": "presentation.json not found"}), 400
    
    try:
        with open(pres_path, "r") as f:
            presentation = json.load(f)
        
        videos_dir = job_dir / "videos"
        videos_dir.mkdir(exist_ok=True)
        
        results = []
        for section in presentation.get("sections", []):
            sid = section.get("section_id") or section.get("id")
            if sid not in section_ids:
                continue
            
            video_prompts = section.get("video_prompts", [])
            if not video_prompts:
                results.append({
                    "section_id": sid,
                    "status": "skipped",
                    "reason": "No video_prompts"
                })
                continue
            
            print(f"[API] Generating videos for section {sid} ({len(video_prompts)} prompts)")
            
            try:
                video_paths = render_from_video_prompts(
                    section=section,
                    output_dir=str(videos_dir),
                    dry_run=dry_run,
                    skip_wan=skip_wan
                )
                
                section_type = section.get("section_type", "content")
                if video_paths and not dry_run:
                    if section_type == "recap":
                        section["recap_video_paths"] = [f"videos/{Path(p).name}" for p in video_paths if p.endswith('.mp4')]
                    else:
                        section["content_video_path"] = f"videos/topic_{sid}.mp4"
                        section["beat_video_paths"] = [f"videos/{Path(p).name}" for p in video_paths if 'beat' in Path(p).name]
                    section["has_content_video"] = True
                
                results.append({
                    "section_id": sid,
                    "status": "success",
                    "videos": video_paths
                })
            except WanRenderError as e:
                results.append({
                    "section_id": sid,
                    "status": "error",
                    "error": str(e)
                })
            except Exception as e:
                results.append({
                    "section_id": sid,
                    "status": "error",
                    "error": str(e)
                })
        
        if not dry_run:
            with open(pres_path, "w") as f:
                json.dump(presentation, f, indent=2)
        
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "results": results,
            "dry_run": dry_run,
            "skip_wan": skip_wan,
            "presentation_updated": not dry_run
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "job_id": job_id
        }), 500


@app.route("/api/v14/pipeline-info", methods=["GET"])
def get_v14_pipeline_info():
    """Return V1.4 pipeline architecture information."""
    return jsonify(get_pipeline_info())


@app.route("/api/v14/generate", methods=["POST"])
def generate_v14():
    """
    V1.4 Split Director Pipeline endpoint.
    
    Request body (JSON):
    - markdown: Markdown content to process (required)
    - subject: Subject area (default: "General Science")
    - grade: Grade level (default: "9")
    - skip_wan: If true, skips WAN video rendering (default: false) 
    - tts_provider: TTS provider - "narakeet" (production), "pyttsx3" (dry run local), "estimate" (default: "narakeet")
    
    Returns:
    - presentation.json following v1.3 schema with spec_version v1.4
    - analytics data including token usage and timing
    - validation results
    """
    try:
        if is_job_running():
            current_id = get_current_job_id()
            return jsonify({
                "status": "busy",
                "message": "A job is already running. Please wait for it to complete.",
                "current_job_id": current_id
            }), 409
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400
        
        markdown_content = data.get("markdown", "")
        if not markdown_content:
            return jsonify({"error": "markdown field is required"}), 400
        
        subject = data.get("subject", "General Science")
        grade = data.get("grade", "9")
        skip_wan = data.get("skip_wan", False)
        tts_provider = data.get("tts_provider", "narakeet")
        
        if tts_provider not in ["narakeet", "pyttsx3", "estimate"]:
            return jsonify({"error": f"Invalid tts_provider: {tts_provider}. Use 'narakeet', 'pyttsx3', or 'estimate'"}), 400
        
        job_id = job_manager.create_job("v14_pipeline", {
            "subject": subject,
            "grade": grade,
            "skip_wan": skip_wan,
            "tts_provider": tts_provider,
            "content_preview": markdown_content[:200] + "..." if len(markdown_content) > 200 else markdown_content
        })
        
        job_output_dir = JOBS_DIR / job_id
        setup_job_folder(job_output_dir)
        
        def status_callback(jid, phase, message):
            job_manager.update_job(jid, {
                "current_phase_key": phase,
                "status_message": message
            }, persist=True)
        
        generate_tts = tts_provider != "estimate"
        
        presentation, tracker = process_markdown_to_presentation_v14(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            job_id=job_id,
            update_status_callback=status_callback,
            generate_tts=generate_tts,
            output_dir=job_output_dir,
            tts_provider=tts_provider
        )
        
        validation = validate_presentation_v14(presentation)
        
        pres_path = job_output_dir / "presentation.json"
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        analytics_summary = tracker.get_summary() if hasattr(tracker, 'get_summary') else {}
        
        job_manager.update_job(job_id, {
            "status": "completed" if not validation.get("has_errors") else "failed",
            "progress": 100,
            "validation": validation
        }, persist=True)
        
        return jsonify({
            "status": "success" if not validation.get("has_errors") else "validation_failed",
            "job_id": job_id,
            "presentation": presentation,
            "validation": validation,
            "analytics": analytics_summary,
            "output_path": str(pres_path),
            "skip_wan": skip_wan,
            "tts_provider": tts_provider
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/api/v14/dry-run-test", methods=["POST"])
def dry_run_test_v14():
    """
    Dry run test for V1.4 pipeline.
    
    This endpoint runs the full pipeline but captures output without actually
    calling LLMs or TTS services. Useful for validating pipeline structure.
    
    Request body (JSON):
    - markdown: Markdown content (optional, uses sample if not provided)
    - subject: Subject area (default: "Biology")
    - grade: Grade level (default: "10")
    
    Returns:
    - Pipeline info and expected flow
    - Sample topics structure
    - Expected section structure
    """
    try:
        data = request.get_json() or {}
        
        sample_markdown = data.get("markdown") or """
# Cell Structure and Function

## Introduction
Cells are the basic building blocks of all living organisms. Understanding cell structure is fundamental to biology.

## Cell Membrane
The cell membrane is a semi-permeable barrier that controls what enters and exits the cell.
- Made of phospholipid bilayer
- Contains proteins for transport
- Maintains cell homeostasis

### Transport Mechanisms
1. **Passive Transport**: Movement without energy (diffusion, osmosis)
2. **Active Transport**: Requires ATP energy

## Example: Red Blood Cells
Red blood cells demonstrate osmosis:
- In hypotonic solution: cells swell and burst
- In hypertonic solution: cells shrink
- In isotonic solution: cells remain normal

## Summary
Cells are complex structures with specialized components working together to maintain life.
"""
        
        subject = data.get("subject", "Biology")
        grade = data.get("grade", "10")
        
        pipeline_info = get_pipeline_info()
        
        expected_topics = {
            "source_topic": "Cell Structure and Function",
            "topics": [
                {
                    "topic_id": "t1",
                    "title": "Cell Membrane",
                    "concept_type": "definition",
                    "has_formula": False,
                    "suggested_renderer": "video"
                },
                {
                    "topic_id": "t2", 
                    "title": "Transport Mechanisms",
                    "concept_type": "process",
                    "has_formula": False,
                    "suggested_renderer": "video"
                },
                {
                    "topic_id": "t3",
                    "title": "Red Blood Cells Osmosis",
                    "concept_type": "example",
                    "has_formula": False,
                    "suggested_renderer": "video"
                }
            ]
        }
        
        expected_sections = {
            "from_content_director": ["intro", "summary", "content", "example", "quiz"],
            "from_recap_director": ["memory", "recap"],
            "merge_result_order": ["intro", "summary", "content", "example", "quiz", "memory", "recap"]
        }
        
        validation_criteria = {
            "memory": {
                "flashcard_count": 5,
                "mnemonic_style": "R-A-S letters"
            },
            "recap": {
                "video_prompt_count": 5,
                "per_prompt_min_words": 300,
                "total_narration_words": "300-500",
                "avatar": "MUST be hidden"
            }
        }
        
        return jsonify({
            "status": "dry_run_complete",
            "pipeline_version": pipeline_info["version"],
            "pipeline_architecture": pipeline_info["architecture"],
            "passes": pipeline_info["passes"],
            "models": pipeline_info["models"],
            "retry_strategy": pipeline_info["retry_strategy"],
            "test_input": {
                "subject": subject,
                "grade": grade,
                "markdown_length": len(sample_markdown),
                "markdown_preview": sample_markdown[:300] + "..."
            },
            "expected_output": {
                "topics": expected_topics,
                "sections": expected_sections,
                "validation_criteria": validation_criteria
            },
            "next_steps": [
                "Use /api/v14/generate with actual markdown to run full pipeline",
                "Set skip_tts=true to avoid Narakeet costs during testing",
                "Set dry_run=true for fastest iteration"
            ]
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/dashboard")
@app.route("/dashboard/")
def serve_dashboard():
    return send_from_directory(PLAYER_DIR, "dashboard.html")

@app.route("/player/")
@app.route("/player/<path:filename>")
def serve_player(filename="index.html"):
    return send_from_directory(PLAYER_DIR, filename)

@app.route("/player/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory(ASSETS_DIR, filename)

@app.route("/player/jobs/<job_id>/")
def serve_job_player_old(job_id):
    """Legacy route - redirect to new structure"""
    return redirect(f"/jobs/{job_id}/")

@app.route("/jobs/<job_id>/")
def serve_job_player(job_id):
    """Serve job-specific player with all assets in one folder"""
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found"}), 404
    # Serve index.html from job folder (copied during job creation)
    if (job_dir / "index.html").exists():
        return send_from_directory(job_dir, "index.html")
    # Fallback to main player if not copied yet
    return send_from_directory(PLAYER_DIR, "index.html")

@app.route("/jobs/<job_id>/<path:filename>")
def serve_job_assets(job_id, filename):
    """Serve all job assets from job folder"""
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found"}), 404
    # Check if file exists in job folder
    if (job_dir / filename).exists():
        return send_from_directory(job_dir, filename)
    # Fallback to main player folder for shared assets
    if (PLAYER_DIR / filename).exists():
        return send_from_directory(PLAYER_DIR, filename)
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
