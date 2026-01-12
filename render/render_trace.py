import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading

_trace_lock = threading.Lock()

DEFAULT_TRACE_PATH = "player/assets/render_prompts.json"
_current_trace_path = DEFAULT_TRACE_PATH
_current_output_dir = None

def set_trace_output_dir(output_dir: str):
    """Set the output directory for render trace."""
    global _current_trace_path, _current_output_dir
    _current_output_dir = output_dir
    _current_trace_path = os.path.join(output_dir, "render_prompts.json")

def get_trace_path(output_dir: Optional[str] = None) -> str:
    """Get the trace file path, optionally using a specific output directory."""
    if output_dir:
        return os.path.join(output_dir, "render_prompts.json")
    return _current_trace_path

def log_render_prompt(section_id: int, section_title: str, renderer: str, 
                       prompt: str, output_path: str, extra_data: Optional[dict] = None,
                       trace_output_dir: Optional[str] = None):
    """Log render prompt to trace file for debugging and analysis."""
    
    trace_path = get_trace_path(trace_output_dir)
    os.makedirs(os.path.dirname(trace_path), exist_ok=True)
    
    with _trace_lock:
        trace_data = []
        if os.path.exists(trace_path):
            try:
                with open(trace_path, "r", encoding="utf-8") as f:
                    trace_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                trace_data = []
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "section_id": section_id,
            "section_title": section_title,
            "renderer": renderer,
            "prompt": prompt,
            "output_path": output_path
        }
        
        if extra_data:
            entry["extra"] = extra_data
        
        trace_data.append(entry)
        
        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, indent=2)
    
    print(f"[RENDER TRACE] Logged {renderer} prompt for section {section_id}: {section_title}")

def clear_render_trace(output_dir: Optional[str] = None):
    """Clear the render trace file for a new job and set the output directory."""
    global _current_trace_path, _current_output_dir
    
    if output_dir:
        _current_output_dir = output_dir
        _current_trace_path = os.path.join(output_dir, "render_prompts.json")
    else:
        _current_output_dir = None
        _current_trace_path = DEFAULT_TRACE_PATH
    
    trace_path = get_trace_path(output_dir)
    if os.path.exists(trace_path):
        os.remove(trace_path)
