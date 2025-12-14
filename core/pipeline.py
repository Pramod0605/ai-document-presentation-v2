import os
import json
from pathlib import Path
from datetime import datetime

from core.datalab_client import pdf_to_markdown
from core.llm_client import generate_presentation_plan
from core.renderer_executor import render_all_topics
from tts.generate_audio import generate_all_audio

PLAYER_ASSETS_DIR = Path(__file__).parent.parent / "player" / "assets"

def process_pdf_to_videos(
    pdf_path: str,
    subject: str = "General Science",
    grade: str = "9",
    output_dir: str = None
) -> dict:
    output_dir = output_dir or str(PLAYER_ASSETS_DIR)
    videos_dir = Path(output_dir) / "videos"
    audio_dir = Path(output_dir) / "audio"
    
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    
    job_status = {
        "status": "processing",
        "started_at": datetime.now().isoformat(),
        "steps": []
    }
    
    try:
        job_status["steps"].append({"step": "pdf_to_markdown", "status": "started"})
        markdown_content = pdf_to_markdown(pdf_path)
        job_status["steps"][-1]["status"] = "completed"
        
        job_status["steps"].append({"step": "generate_presentation_plan", "status": "started"})
        presentation, generation_trace = generate_presentation_plan(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade
        )
        job_status["steps"][-1]["status"] = "completed"
        
        presentation_path = Path(output_dir) / "presentation.json"
        with open(presentation_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        trace_path = Path(output_dir) / "generation_trace.json"
        with open(trace_path, "w") as f:
            json.dump(generation_trace, f, indent=2)
        
        job_status["steps"].append({"step": "render_videos", "status": "started"})
        rendered_videos = render_all_topics(presentation, str(videos_dir))
        
        success_count = sum(1 for v in rendered_videos if v.get("status") == "success")
        fail_count = len(rendered_videos) - success_count
        
        job_status["steps"][-1]["status"] = "completed" if fail_count == 0 else "partial"
        job_status["steps"][-1]["videos"] = rendered_videos
        job_status["steps"][-1]["success_count"] = success_count
        job_status["steps"][-1]["fail_count"] = fail_count
        
        job_status["steps"].append({"step": "generate_audio", "status": "started"})
        audio_files = generate_all_audio(presentation, str(audio_dir))
        job_status["steps"][-1]["status"] = "completed"
        job_status["steps"][-1]["audio_files"] = audio_files
        
        job_status["status"] = "completed"
        job_status["completed_at"] = datetime.now().isoformat()
        job_status["presentation_path"] = str(presentation_path)
        job_status["trace_path"] = str(trace_path)
        job_status["topics_count"] = len(presentation.get("topics", []))
        
    except Exception as e:
        job_status["status"] = "failed"
        job_status["error"] = str(e)
        job_status["failed_at"] = datetime.now().isoformat()
        raise
    
    return job_status

def process_markdown_to_videos(
    markdown_content: str,
    subject: str = "General Science",
    grade: str = "9",
    output_dir: str = None
) -> dict:
    output_dir = output_dir or str(PLAYER_ASSETS_DIR)
    videos_dir = Path(output_dir) / "videos"
    audio_dir = Path(output_dir) / "audio"
    
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    
    job_status = {
        "status": "processing",
        "started_at": datetime.now().isoformat(),
        "steps": []
    }
    
    try:
        job_status["steps"].append({"step": "generate_presentation_plan", "status": "started"})
        presentation, generation_trace = generate_presentation_plan(
            markdown_content=markdown_content,
            subject=subject,
            grade=grade
        )
        job_status["steps"][-1]["status"] = "completed"
        
        presentation_path = Path(output_dir) / "presentation.json"
        with open(presentation_path, "w") as f:
            json.dump(presentation, f, indent=2)
        
        trace_path = Path(output_dir) / "generation_trace.json"
        with open(trace_path, "w") as f:
            json.dump(generation_trace, f, indent=2)
        
        job_status["steps"].append({"step": "render_videos", "status": "started"})
        rendered_videos = render_all_topics(presentation, str(videos_dir))
        
        success_count = sum(1 for v in rendered_videos if v.get("status") == "success")
        fail_count = len(rendered_videos) - success_count
        
        job_status["steps"][-1]["status"] = "completed" if fail_count == 0 else "partial"
        job_status["steps"][-1]["videos"] = rendered_videos
        job_status["steps"][-1]["success_count"] = success_count
        job_status["steps"][-1]["fail_count"] = fail_count
        
        job_status["steps"].append({"step": "generate_audio", "status": "started"})
        audio_files = generate_all_audio(presentation, str(audio_dir))
        job_status["steps"][-1]["status"] = "completed"
        job_status["steps"][-1]["audio_files"] = audio_files
        
        job_status["status"] = "completed"
        job_status["completed_at"] = datetime.now().isoformat()
        job_status["presentation_path"] = str(presentation_path)
        job_status["trace_path"] = str(trace_path)
        job_status["topics_count"] = len(presentation.get("topics", []))
        
    except Exception as e:
        job_status["status"] = "failed"
        job_status["error"] = str(e)
        job_status["failed_at"] = datetime.now().isoformat()
        raise
    
    return job_status
