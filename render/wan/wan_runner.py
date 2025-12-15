from pathlib import Path
from .wan_client import WANClient
from render.render_trace import log_render_prompt

def render_wan_video(topic: dict, output_dir: str, dry_run: bool = False) -> str:
    topic_id = topic.get("id", 1)
    topic_title = topic.get("title", "Untitled")
    explanation_plan = topic.get("explanation_plan", {})
    wan_prompt = explanation_plan.get("wan_prompt", "Educational visualization")
    duration = topic.get("duration", 30)
    
    output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")
    
    # Log the prompt before rendering
    log_render_prompt(
        section_id=topic_id,
        section_title=topic_title,
        renderer="wan",
        prompt=wan_prompt,
        output_path=output_path,
        extra_data={"duration": duration, "dry_run": dry_run}
    )
    
    # In dry_run mode, create a placeholder instead of calling the API
    if dry_run:
        print(f"[DRY RUN] Skipping WAN video generation for topic {topic_id}")
        return _create_dry_run_placeholder(topic_id, output_path, duration)
    
    client = WANClient()
    result_path = client.generate_video(
        prompt=wan_prompt,
        duration=min(duration, 60),
        output_path=output_path
    )
    
    return result_path

def _create_dry_run_placeholder(topic_id: int, output_path: str, duration: int) -> str:
    """Create a simple marker file for dry run mode (no actual video rendering)."""
    import os
    marker_path = output_path.replace(".mp4", ".dry_run.txt")
    with open(marker_path, "w") as f:
        f.write(f"DRY RUN placeholder for topic {topic_id}\n")
        f.write(f"Duration: {duration}s\n")
        f.write(f"Output would be: {output_path}\n")
    print(f"[DRY RUN] Created marker file: {marker_path}")
    return marker_path
