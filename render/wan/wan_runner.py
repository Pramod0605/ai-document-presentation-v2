from pathlib import Path
from .wan_client import WANClient
from render.render_trace import log_render_prompt

def render_wan_video(topic: dict, output_dir: str, dry_run: bool = False, skip_wan: bool = False, trace_output_dir: str = None) -> str:
    topic_id = topic.get("id", 1)
    topic_title = topic.get("title", "Untitled")
    explanation_plan = topic.get("explanation_plan", {})
    wan_prompt = explanation_plan.get("wan_prompt", "Educational visualization")
    duration = topic.get("duration", 30)
    
    output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")
    
    log_render_prompt(
        section_id=topic_id,
        section_title=topic_title,
        renderer="wan",
        prompt=wan_prompt,
        output_path=output_path,
        extra_data={"duration": duration, "dry_run": dry_run, "skip_wan": skip_wan},
        trace_output_dir=trace_output_dir
    )
    
    if dry_run:
        print(f"[DRY RUN] Skipping WAN video generation for topic {topic_id}")
        return _create_dry_run_placeholder(topic_id, output_path, duration)
    
    if skip_wan:
        print(f"[SKIP WAN] Using placeholder video for topic {topic_id}")
        return _create_placeholder_video(topic_id, topic_title, output_path, duration)
    
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

def _create_placeholder_video(topic_id: int, topic_title: str, output_path: str, duration: int) -> str:
    """Create a simple placeholder video when skip_wan is enabled."""
    try:
        from moviepy import ColorClip, TextClip, CompositeVideoClip
        
        bg = ColorClip(size=(1280, 720), color=(30, 60, 90), duration=min(duration, 10))
        
        try:
            txt = TextClip(
                text=f"Topic {topic_id}: {topic_title[:40]}...",
                font_size=36,
                color="white",
                size=(1280, 720)
            )
            txt = txt.with_position("center").with_duration(min(duration, 10))
            video = CompositeVideoClip([bg, txt])
        except Exception:
            video = bg
        
        video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio=False,
            verbose=False,
            logger=None
        )
        video.close()
        print(f"[SKIP WAN] Created placeholder video: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Placeholder creation failed: {e}, creating minimal video")
        from moviepy import ColorClip
        clip = ColorClip(size=(1280, 720), color=(30, 60, 90), duration=5)
        clip.write_videofile(output_path, fps=24, codec="libx264", audio=False, verbose=False, logger=None)
        clip.close()
        return output_path
