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
from core.pipeline_v14 import get_pipeline_info, process_markdown_to_presentation_v14, process_with_renderers_v14, validate_presentation_v14
from core.pipeline_v15 import process_markdown_to_presentation_v15, PipelineError as PipelineV15Error
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
        tts_provider = request.form.get("tts_provider", "edge")
        pipeline_version = request.form.get("pipeline_version", "v15")
        
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
            
            job_type_name = "v15_pipeline" if pipeline_version == "v15" else "v14_pipeline"
            job_id = job_manager.create_job(job_type_name, {
                "subject": subject,
                "grade": grade,
                "file_path": str(temp_file),
                "source_file": original_filename,
                "skip_wan": skip_wan,
                "skip_avatar": skip_avatar,
                "tts_provider": tts_provider,
                "pipeline_version": pipeline_version
            })
            
            job_output_dir = JOBS_DIR / job_id
            setup_job_folder(job_output_dir)
            
            if job_type == "pdf":
                pdf_processor = process_pdf_job_v15 if pipeline_version == "v15" else process_pdf_job
                run_job_async(
                    job_id,
                    pdf_processor,
                    pdf_path=str(temp_file),
                    subject=subject,
                    grade=grade,
                    output_dir=str(job_output_dir),
                    dry_run=dry_run,
                    skip_wan=skip_wan,
                    skip_avatar=skip_avatar,
                    source_file=original_filename,
                    tts_provider=tts_provider
                )
            else:
                with open(temp_file, "r", encoding="utf-8") as f:
                    markdown_content = f.read()
                os.unlink(temp_file)
                
                content_preview = markdown_content[:300].replace('\n', ' ').strip()
                if len(markdown_content) > 300:
                    content_preview += "..."
                
                job_manager.update_job(job_id, {"content_preview": content_preview}, persist=True)
                
                job_processor = process_markdown_job_v15 if pipeline_version == "v15" else process_markdown_job
                run_job_async(
                    job_id,
                    job_processor,
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
            tts_provider = data.get("tts_provider", "edge")
            pipeline_version = data.get("pipeline_version", "v15")
            
            if not markdown_content:
                return jsonify({"error": "Markdown content is required"}), 400
            
            content_preview = markdown_content[:300].replace('\n', ' ').strip()
            if len(markdown_content) > 300:
                content_preview += "..."
            
            job_type_name = "v15_pipeline" if pipeline_version == "v15" else "v14_pipeline"
            job_id = job_manager.create_job(job_type_name, {
                "subject": subject,
                "grade": grade,
                "dry_run": dry_run,
                "skip_wan": skip_wan,
                "skip_avatar": skip_avatar,
                "tts_provider": tts_provider,
                "pipeline_version": pipeline_version,
                "content_preview": content_preview
            })
            
            job_output_dir = JOBS_DIR / job_id
            setup_job_folder(job_output_dir)
            
            job_processor = process_markdown_job_v15 if pipeline_version == "v15" else process_markdown_job
            run_job_async(
                job_id,
                job_processor,
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


@app.route("/job/<job_id>/analytics", methods=["GET"])
def get_job_analytics(job_id):
    """Get analytics data for a completed job."""
    job = job_manager.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    # Try to load analytics.json from job folder
    job_folder = Path(JOBS_DIR) / job_id
    analytics_path = job_folder / "analytics.json"
    
    if analytics_path.exists():
        try:
            with open(analytics_path, 'r') as f:
                analytics_data = json.load(f)
            return jsonify({
                "job_id": job_id,
                "has_analytics": True,
                "analytics": analytics_data
            })
        except Exception as e:
            return jsonify({
                "job_id": job_id,
                "has_analytics": False,
                "error": f"Failed to load analytics: {str(e)}"
            }), 500
    else:
        # No analytics file - return basic job info
        return jsonify({
            "job_id": job_id,
            "has_analytics": False,
            "message": "Analytics not available for this job (pre-analytics feature or failed early)",
            "basic_info": {
                "status": job["status"],
                "created_at": job["created_at"],
                "completed_at": job.get("completed_at"),
                "error": job.get("error")
            }
        })


def process_pdf_job(job_id: str, pdf_path: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None, tts_provider: str = "edge") -> dict:
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


def process_pdf_job_v15(job_id: str, pdf_path: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None, tts_provider: str = "edge") -> dict:
    """Process PDF using V1.5 Split Agent pipeline.
    
    1. Convert PDF to Markdown using Datalab API
    2. Run V1.5 pipeline on the markdown
    """
    from core.datalab_client import pdf_to_markdown, DatalabConversionError
    from pathlib import Path
    
    try:
        job_manager.update_job(job_id, {
            "current_phase_key": "pdf_conversion",
            "status_message": "Converting PDF to Markdown..."
        }, persist=True)
        
        markdown_content = pdf_to_markdown(pdf_path)
        
        # Save raw markdown for comparison/debugging
        source_md_path = Path(output_dir) / "source_markdown.md"
        with open(source_md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"[V1.5] Saved source markdown to {source_md_path} ({len(markdown_content)} chars)")
        
        content_preview = markdown_content[:300].replace('\n', ' ').strip()
        if len(markdown_content) > 300:
            content_preview += "..."
        job_manager.update_job(job_id, {"content_preview": content_preview}, persist=True)
        
        def status_callback(jid, phase, message):
            job_manager.update_job(jid, {
                "current_phase_key": phase,
                "status_message": message
            }, persist=True)
        
        generate_tts = tts_provider != "estimate"
        output_path = Path(output_dir)
        
        presentation, tracker = process_markdown_to_presentation_v15(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            job_id=job_id,
            update_status_callback=status_callback,
            generate_tts=generate_tts,
            output_dir=output_path,
            tts_provider=tts_provider,
            dry_run=dry_run,
            skip_wan=skip_wan
        )
        
        pres_path = output_path / "presentation.json"
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        analytics_summary = tracker.get_summary() if hasattr(tracker, 'get_summary') else {}
        
        return {
            "status": "success",
            "presentation": presentation,
            "analytics": analytics_summary,
            "output_path": str(pres_path),
            "pipeline_version": "1.5",
            "source_type": "pdf"
        }
    except DatalabConversionError as e:
        raise RuntimeError(f"PDF conversion failed: {e}")
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


def process_markdown_job(job_id: str, markdown_content: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None, tts_provider: str = "edge") -> dict:
    """Process markdown using V1.4 Hybrid pipeline (Split Directors + V1.3 infrastructure)."""
    result = process_markdown_to_videos(
        markdown_content=markdown_content,
        subject=subject,
        grade=grade,
        output_dir=output_dir,
        job_id=job_id,
        dry_run=dry_run,
        skip_wan=skip_wan,
        skip_avatar=skip_avatar,
        source_file=source_file,
        use_remotion=True
    )
    return result


def process_markdown_job_v15(job_id: str, markdown_content: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None, tts_provider: str = "edge") -> dict:
    """Process markdown using V1.5 Split Agent pipeline."""
    from pathlib import Path
    
    # Save raw markdown for comparison/debugging
    output_path = Path(output_dir)
    source_md_path = output_path / "source_markdown.md"
    with open(source_md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"[V1.5] Saved source markdown to {source_md_path} ({len(markdown_content)} chars)")
    
    def status_callback(jid, phase, message):
        job_manager.update_job(jid, {
            "current_phase_key": phase,
            "status_message": message
        }, persist=True)
    
    generate_tts = tts_provider != "estimate"
    
    presentation, tracker = process_markdown_to_presentation_v15(
        markdown_content=markdown_content,
        subject=subject,
        grade=grade,
        job_id=job_id,
        update_status_callback=status_callback,
        generate_tts=generate_tts,
        output_dir=output_path,
        tts_provider=tts_provider,
        dry_run=dry_run,
        skip_wan=skip_wan
    )
    
    pres_path = output_path / "presentation.json"
    with open(pres_path, "w") as f:
        json.dump(presentation, f, indent=2)
    
    analytics_summary = tracker.get_summary() if hasattr(tracker, 'get_summary') else {}
    
    return {
        "status": "success",
        "presentation": presentation,
        "analytics": analytics_summary,
        "output_path": str(pres_path),
        "pipeline_version": "1.5"
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


@app.route("/jobs/<job_id>/resume-recap", methods=["POST"])
def resume_job_from_recap(job_id):
    """Resume a V1.5 job from the recap stage.
    
    Use when the job failed at recap narration/scene generation.
    Loads existing artifacts and continues from recap.
    
    POST body (optional):
    - skip_wan: boolean (default: false)
    - dry_run: boolean (default: false)
    """
    from core.pipeline_v15 import resume_from_recap, PipelineError
    
    data = request.get_json() or {}
    skip_wan = data.get("skip_wan", False)
    dry_run = data.get("dry_run", False)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    artifacts_dir = job_dir / "artifacts"
    if not artifacts_dir.exists():
        return jsonify({
            "error": "Artifacts directory not found. Job must have completed section processing.",
            "job_id": job_id
        }), 400
    
    chunker_path = artifacts_dir / "01_chunker.json"
    if not chunker_path.exists():
        return jsonify({
            "error": "01_chunker.json not found. Cannot resume without source content.",
            "job_id": job_id
        }), 400
    
    with open(chunker_path) as f:
        chunker_data = json.load(f)
    
    chunks = chunker_data.get("chunks", [])
    markdown_content = "\n\n".join([c.get("content", "") for c in chunks])
    
    subject = chunker_data.get("subject", "General")
    grade = chunker_data.get("grade", "General")
    
    try:
        print(f"[API] Resuming job {job_id} from recap stage")
        
        def status_callback(phase, message):
            print(f"[Resume {job_id}] {phase}: {message}")
        
        presentation, tracker = resume_from_recap(
            job_id=job_id,
            output_dir=job_dir,
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            generate_tts=True,
            run_renderers=True,
            dry_run=dry_run,
            skip_wan=skip_wan,
            status_callback=status_callback
        )
        
        pres_path = job_dir / "presentation.json"
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        for filename in ["index.html", "player.js"]:
            src = PLAYER_DIR / filename
            dst = job_dir / filename
            if src.exists():
                shutil.copy(str(src), str(dst))
        
        # Update job_manager status so dashboard shows completed
        sections_count = len(presentation.get("sections", []))
        job_manager.update_job(job_id, {
            "status": "completed",
            "progress": 100,
            "current_step_name": "Complete",
            "status_message": f"Resumed from recap - {sections_count} sections rendered",
            "completed_at": __import__('datetime').datetime.utcnow().isoformat(),
            "error": None
        }, persist=True)
        
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "sections_count": sections_count,
            "message": "Job resumed from recap stage successfully"
        })
        
    except PipelineError as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "phase": e.phase,
            "job_id": job_id
        }), 500
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


@app.route("/jobs/<job_id>/regenerate_and_render", methods=["POST"])
def regenerate_and_render(job_id):
    """Regenerate render specs using updated prompts and execute renderers.
    
    POST body:
    - section_ids: List of section IDs to regenerate (required)
    - renderers: List of renderer types to regenerate ["manim", "wan", "all"] (default: ["all"])
    - execute: Whether to execute renderers after generating specs (default: true)
    - skip_wan: Skip WAN API calls during execution (default: false)
    - dry_run: Only generate specs, don't execute (default: false)
    
    This endpoint:
    1. Regenerates render specs (manim_scene_spec, video_prompts) via LLM with updated prompts
    2. Optionally executes the renderers to create actual video files
    """
    from core.llm_client_v12 import pass2_manim_renderer, pass2_video_renderer, rerender_sections_wan
    from core.renderer_executor import render_all_topics, enforce_renderer_policy
    from core.analytics import create_tracker
    
    data = request.get_json() or {}
    section_ids = data.get("section_ids", [])
    renderers = data.get("renderers", ["all"])
    execute = data.get("execute", True)
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
        
        tracker = create_tracker(job_id)
        videos_dir = job_dir / "videos"
        videos_dir.mkdir(exist_ok=True)
        
        results = {"regenerated": [], "render_results": []}
        do_all = "all" in renderers
        do_manim = do_all or "manim" in renderers
        do_wan = do_all or "wan" in renderers
        
        for section in presentation.get("sections", []):
            sid = section.get("section_id") or section.get("id")
            if sid not in section_ids:
                continue
            
            renderer = section.get("renderer", "none")
            section_title = section.get("title", "")[:40]
            
            try:
                if renderer == "manim" and do_manim:
                    print(f"[Regenerate] Section {sid}: Regenerating manim spec...")
                    manim_result = pass2_manim_renderer(section, tracker)
                    section["manim_scene_spec"] = manim_result.get("manim_scene_spec")
                    results["regenerated"].append({
                        "section_id": sid,
                        "title": section_title,
                        "renderer": "manim",
                        "status": "success",
                        "objects": len(section.get("manim_scene_spec", {}).get("objects", [])),
                        "animations": len(section.get("manim_scene_spec", {}).get("animation_sequence", []))
                    })
                    
                elif renderer in ["video", "wan_video", "wan"] and do_wan:
                    print(f"[Regenerate] Section {sid}: Regenerating WAN video prompts...")
                    video_result = pass2_video_renderer(section, tracker)
                    section["video_prompts"] = video_result.get("video_prompts", [])
                    results["regenerated"].append({
                        "section_id": sid,
                        "title": section_title,
                        "renderer": renderer,
                        "status": "success",
                        "prompts_count": len(section.get("video_prompts", []))
                    })
                else:
                    results["regenerated"].append({
                        "section_id": sid,
                        "title": section_title,
                        "renderer": renderer,
                        "status": "skipped",
                        "reason": f"Renderer {renderer} not in requested types"
                    })
                    
            except Exception as e:
                results["regenerated"].append({
                    "section_id": sid,
                    "title": section_title,
                    "renderer": renderer,
                    "status": "error",
                    "error": str(e)
                })
        
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        if execute and not dry_run:
            print(f"[Regenerate] Executing renderers for sections {section_ids}...")
            presentation = enforce_renderer_policy(presentation)
            
            rendered_videos = render_all_topics(
                presentation=presentation,
                output_dir=str(videos_dir),
                dry_run=False,
                skip_wan=skip_wan,
                output_dir_base=str(job_dir)
            )
            
            for result in rendered_videos:
                topic_id = result.get("topic_id")
                if topic_id in section_ids:
                    video_path = result.get("video_path")
                    for section in presentation.get("sections", []):
                        if section.get("section_id") == topic_id:
                            if video_path:
                                rel_path = Path(video_path).name if "/" in str(video_path) else video_path
                                section["video_path"] = f"videos/{rel_path}"
                            break
                    
                    results["render_results"].append({
                        "section_id": topic_id,
                        "status": result.get("status"),
                        "video_path": result.get("video_path"),
                        "error": result.get("error")
                    })
            
            with open(pres_path, "w") as f:
                json.dump(presentation, f, indent=2)
        
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "results": results,
            "execute": execute,
            "dry_run": dry_run,
            "skip_wan": skip_wan
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
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
        
        if not validation.get("has_errors"):
            status_callback(job_id, "renderers", "Generating video content...")
            presentation = process_with_renderers_v14(
                presentation=presentation,
                tracker=tracker,
                job_id=job_id,
                update_status_callback=status_callback,
                use_remotion=True,
                output_dir=job_output_dir,
                dry_run=False,
                skip_wan=skip_wan
            )
        
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


@app.route("/api/v15/pipeline-info", methods=["GET"])
def get_v15_pipeline_info():
    """Return V1.5 pipeline architecture information."""
    return jsonify({
        "version": "1.5",
        "name": "Split Agent Architecture",
        "agents": [
            {"name": "SmartChunker", "output_fields": "5-10"},
            {"name": "SectionPlanner", "output_fields": "10"},
            {"name": "NarrationWriter", "output_fields": "5"},
            {"name": "VisualSpecArtist", "output_fields": "12"},
            {"name": "RendererSpecAgent", "output_fields": "variable"},
            {"name": "MemoryFlashcard", "output_fields": "5"},
            {"name": "RecapScene", "output_fields": "5"}
        ],
        "flow": [
            "SmartChunker → topics",
            "SectionPlanner(topics) → section_blueprints",
            "FOR EACH blueprint: NarrationWriter → VisualSpecArtist → RendererSpec",
            "MemoryFlashcardAgent → memory_section",
            "RecapSceneAgent → recap_section",
            "MergeStep → presentation.json",
            "TTS → audio + durations",
            "Renderers → video files"
        ],
        "improvements": [
            "5-15 fields per agent (vs 50+ in V1.4)",
            "Per-agent retries instead of full pipeline restarts",
            "Focused prompts for better quality"
        ]
    })


@app.route("/api/v15/generate", methods=["POST"])
def generate_v15():
    """
    V1.5 Split Agent Pipeline endpoint.
    
    Request body (JSON):
    - markdown: Markdown content to process (required)
    - subject: Subject area (default: "General Science")
    - grade: Grade level (default: "9")
    - skip_wan: If true, skips WAN video rendering (default: false)
    - tts_provider: TTS provider - "edge" (default, free), "narakeet", or "estimate"
    
    Returns:
    - presentation.json following v1.3 schema with spec_version v1.5
    - analytics data including per-agent token usage
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
        tts_provider = data.get("tts_provider", "edge_tts")
        
        if tts_provider not in ["narakeet", "estimate", "edge", "edge_tts", "pyttsx3"]:
            return jsonify({"error": f"Invalid tts_provider: {tts_provider}. Use 'edge_tts', 'pyttsx3', 'narakeet', or 'estimate'"}), 400
        
        if tts_provider == "edge":
            tts_provider = "edge_tts"
        
        job_id = job_manager.create_job("v15_pipeline", {
            "subject": subject,
            "grade": grade,
            "skip_wan": skip_wan,
            "tts_provider": tts_provider,
            "pipeline_version": "1.5",
            "content_preview": markdown_content[:200] + "..." if len(markdown_content) > 200 else markdown_content
        })
        
        job_manager.start_job(job_id)
        
        job_output_dir = JOBS_DIR / job_id
        setup_job_folder(job_output_dir)
        
        def status_callback(jid, phase, message):
            job_manager.update_job(jid, {
                "current_phase_key": phase,
                "status_message": message
            }, persist=True)
        
        generate_tts = tts_provider not in ["estimate"]
        
        presentation, tracker = process_markdown_to_presentation_v15(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade,
            job_id=job_id,
            update_status_callback=status_callback,
            generate_tts=generate_tts,
            output_dir=job_output_dir,
            tts_provider=tts_provider,
            dry_run=False,
            skip_wan=skip_wan
        )
        
        pres_path = job_output_dir / "presentation.json"
        with open(pres_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        analytics_summary = tracker.get_summary() if hasattr(tracker, 'get_summary') else {}
        
        job_manager.update_job(job_id, {
            "status": "completed",
            "progress": 100,
            "pipeline_version": "1.5"
        }, persist=True)
        
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "presentation": presentation,
            "analytics": analytics_summary,
            "output_path": str(pres_path),
            "pipeline_version": "1.5",
            "skip_wan": skip_wan,
            "tts_provider": tts_provider
        })
        
    except PipelineV15Error as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[V1.5 Pipeline Error] Phase: {e.phase}")
        print(f"[V1.5 Pipeline Error] Error: {str(e)}")
        print(f"[V1.5 Pipeline Error] Traceback:\n{tb}")
        if 'job_id' in locals():
            job_manager.fail_job(job_id, str(e), phase_key=e.phase)
        return jsonify({
            "status": "error",
            "error": str(e),
            "phase": e.phase,
            "traceback": tb
        }), 500
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[V1.5 Pipeline Error] Error: {str(e)}")
        print(f"[V1.5 Pipeline Error] Traceback:\n{tb}")
        if 'job_id' in locals():
            job_manager.fail_job(job_id, str(e))
        return jsonify({
            "status": "error",
            "error": str(e),
            "traceback": tb
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

@app.route("/player_v2/")
@app.route("/player_v2/<path:filename>")
def serve_player_v2(filename="player_v2.html"):
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
