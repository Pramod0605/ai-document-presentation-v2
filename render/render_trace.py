import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

RENDER_TRACE_PATH = "player/assets/render_prompts.json"

def log_render_prompt(section_id: int, section_title: str, renderer: str, 
                       prompt: str, output_path: str, extra_data: Optional[dict] = None):
    """Log render prompt to trace file for debugging and analysis."""
    
    os.makedirs(os.path.dirname(RENDER_TRACE_PATH), exist_ok=True)
    
    trace_data = []
    if os.path.exists(RENDER_TRACE_PATH):
        try:
            with open(RENDER_TRACE_PATH, "r") as f:
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
    
    with open(RENDER_TRACE_PATH, "w") as f:
        json.dump(trace_data, f, indent=2)
    
    print(f"[RENDER TRACE] Logged {renderer} prompt for section {section_id}: {section_title}")

def clear_render_trace():
    """Clear the render trace file for a new job."""
    if os.path.exists(RENDER_TRACE_PATH):
        os.remove(RENDER_TRACE_PATH)
