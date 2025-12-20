import os
import sys
import shutil
import tempfile
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS

from core.pipeline import process_pdf_to_videos
from core.pipeline_v12 import process_markdown_to_videos_v12 as process_markdown_to_videos
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
        "version": "1.1.0",
        "features": ["job_mode", "pdf", "markdown"]
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
            
            job_id = job_manager.create_job(job_type, {
                "subject": subject,
                "grade": grade,
                "file_path": str(temp_file),
                "source_file": original_filename
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
                    source_file=original_filename
                )
        
        elif request.is_json:
            data = request.json
            markdown_content = data.get("markdown", "")
            subject = data.get("subject", subject)
            grade = data.get("grade", grade)
            dry_run = data.get("dry_run", False)
            skip_wan = data.get("skip_wan", False)
            skip_avatar = data.get("skip_avatar", False)
            
            if not markdown_content:
                return jsonify({"error": "Markdown content is required"}), 400
            
            job_id = job_manager.create_job("markdown", {
                "subject": subject,
                "grade": grade,
                "dry_run": dry_run
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
                skip_avatar=skip_avatar
            )
        
        else:
            return jsonify({"error": "Please provide a file or markdown content"}), 400
        
        mode_msg = " (DRY RUN - prompts only, no real rendering)" if dry_run else ""
        return jsonify({
            "status": "accepted",
            "job_id": job_id,
            "dry_run": dry_run,
            "skip_wan": skip_wan,
            "skip_avatar": skip_avatar,
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
    
    return jsonify({
        "job_id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "current_step": job["current_step_name"],
        "steps_completed": job["steps_completed"],
        "total_steps": job["total_steps"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "completed_at": job["completed_at"],
        "error": job["error"]
    })


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


def process_markdown_job(job_id: str, markdown_content: str, subject: str, grade: str, output_dir: str, dry_run: bool = False, skip_wan: bool = False, skip_avatar: bool = False, source_file: Optional[str] = None) -> dict:
    return process_markdown_to_videos(
        markdown_content=markdown_content,
        subject=subject,
        grade=grade,
        output_dir=output_dir,
        job_id=job_id,
        dry_run=dry_run,
        skip_wan=skip_wan,
        skip_avatar=skip_avatar,
        source_file=source_file
    )


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
