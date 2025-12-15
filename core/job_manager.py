import os
import json
import uuid
import threading
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Callable

class JobManager:
    def __init__(self):
        self._jobs: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._execution_lock = threading.Lock()
        self._current_job_id: Optional[str] = None
    
    def create_job(self, job_type: str, params: dict) -> str:
        job_id = str(uuid.uuid4())[:8]
        
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "type": job_type,
                "params": params,
                "status": "queued",
                "current_step": None,
                "current_step_name": "Initializing...",
                "steps_completed": 0,
                "total_steps": 4 if job_type == "pdf" else 3,
                "progress": 0,
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "error": None,
                "result": None
            }
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[dict]:
        with self._lock:
            return self._jobs.get(job_id, None)
    
    def update_job(self, job_id: str, updates: dict):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(updates)
    
    def set_step(self, job_id: str, step_name: str, step_number: int):
        job = self.get_job(job_id)
        if job:
            total = job.get("total_steps", 4)
            progress = int((step_number / total) * 100)
            self.update_job(job_id, {
                "current_step": step_number,
                "current_step_name": step_name,
                "progress": progress
            })
    
    def complete_step(self, job_id: str, step_number: int):
        job = self.get_job(job_id)
        if job:
            total = job.get("total_steps", 4)
            progress = int(((step_number + 1) / total) * 100)
            self.update_job(job_id, {
                "steps_completed": step_number + 1,
                "progress": min(progress, 99)
            })
    
    def complete_job(self, job_id: str, result: dict = None):
        self.update_job(job_id, {
            "status": "completed",
            "progress": 100,
            "completed_at": datetime.now().isoformat(),
            "result": result
        })
    
    def fail_job(self, job_id: str, error: str):
        self.update_job(job_id, {
            "status": "failed",
            "error": error,
            "completed_at": datetime.now().isoformat()
        })
    
    def start_job(self, job_id: str):
        self.update_job(job_id, {
            "status": "processing",
            "started_at": datetime.now().isoformat()
        })


job_manager = JobManager()


def run_job_async(job_id: str, process_func: Callable, **kwargs):
    def worker():
        with job_manager._execution_lock:
            try:
                job_manager._current_job_id = job_id
                job_manager.start_job(job_id)
                result = process_func(job_id=job_id, **kwargs)
                job_manager.complete_job(job_id, result)
            except Exception as e:
                job_manager.fail_job(job_id, str(e))
            finally:
                job_manager._current_job_id = None
    
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


def is_job_running() -> bool:
    return job_manager._current_job_id is not None


def get_current_job_id() -> Optional[str]:
    return job_manager._current_job_id
