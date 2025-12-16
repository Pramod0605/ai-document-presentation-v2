"""
WAN Video Runner - Generates videos from visual beats using Kie.ai API

CRITICAL: Each visual beat becomes a separate video segment.
NO fallback to generic prompts - fail if visual beats are missing.
"""
from pathlib import Path
from typing import List
from .wan_client import WANClient
from render.render_trace import log_render_prompt


class WanRenderError(Exception):
    """Raised when WAN rendering fails and no fallback is allowed."""
    pass


def render_wan_video(topic: dict, output_dir: str, dry_run: bool = False, skip_wan: bool = False, trace_output_dir: str = None) -> str:
    """
    Render WAN video for a section.
    
    For content/example sections with visual_beats:
      - Each beat becomes a separate video segment
      - Returns path to first video (others follow naming pattern)
      
    For intro/summary/memory/recap sections:
      - Uses section-level wan_prompt if provided
      - Fails if no prompt available (no fallback to generic)
    """
    topic_id = topic.get("id", 1)
    topic_title = topic.get("title", "Untitled")
    section_type = topic.get("section_type", "content")
    explanation_plan = topic.get("explanation_plan", {})
    visual_beats = topic.get("visual_beats", [])
    duration = topic.get("duration", 30)
    
    # Check for compiled WAN prompt from visual_compiler
    compiled_wan_prompt = explanation_plan.get("compiled_wan_prompt")
    
    # For content/example sections, use visual beats
    if section_type in ["content", "example"] and visual_beats:
        return _render_visual_beats(
            topic_id=topic_id,
            topic_title=topic_title,
            section_type=section_type,
            visual_beats=visual_beats,
            output_dir=output_dir,
            dry_run=dry_run,
            skip_wan=skip_wan,
            trace_output_dir=trace_output_dir,
            duration=duration
        )
    
    # For other section types, use section-level prompt
    wan_prompt = explanation_plan.get("wan_prompt")
    
    if not wan_prompt and not compiled_wan_prompt:
        raise WanRenderError(
            f"Section {topic_id} ({section_type}): No WAN prompt available. "
            f"Content/example sections must have visual_beats. "
            f"Other sections need explicit wan_prompt in explanation_plan."
        )
    
    # Use compiled prompt if available, else section-level
    prompt = compiled_wan_prompt or wan_prompt
    
    output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")
    
    log_render_prompt(
        section_id=topic_id,
        section_title=topic_title,
        renderer="wan",
        prompt=prompt,
        output_path=output_path,
        extra_data={
            "section_type": section_type,
            "duration": duration, 
            "dry_run": dry_run, 
            "skip_wan": skip_wan,
            "source": "section_level"
        },
        trace_output_dir=trace_output_dir
    )
    
    if dry_run:
        print(f"[DRY RUN] WAN video for section {topic_id}")
        return _create_dry_run_placeholder(topic_id, output_path, duration)
    
    if skip_wan:
        print(f"[SKIP WAN] Placeholder for section {topic_id}")
        return _create_placeholder_video(topic_id, topic_title, output_path, duration)
    
    client = WANClient()
    result_path = client.generate_video(
        prompt=prompt,
        duration=min(duration, 60),
        output_path=output_path
    )
    
    return result_path


def _render_visual_beats(
    topic_id: int,
    topic_title: str,
    section_type: str,
    visual_beats: list,
    output_dir: str,
    dry_run: bool,
    skip_wan: bool,
    trace_output_dir: str,
    duration: int
) -> str:
    """
    Render each visual beat as a separate video segment.
    
    Returns path to first video segment.
    Creates: topic_{id}_beat_{0..n}.mp4
    """
    from core.visual_compiler import compile_wan_prompt, VisualCompilationError
    
    if not visual_beats:
        raise WanRenderError(
            f"Section {topic_id}: {section_type} section has no visual_beats. "
            f"LLM must generate visual beats for content/example sections."
        )
    
    print(f"[WAN] Rendering {len(visual_beats)} visual beats for section {topic_id}")
    
    beat_duration = max(5, duration // len(visual_beats))
    video_paths = []
    client = WANClient() if not skip_wan and not dry_run else None
    
    for beat_idx, beat in enumerate(visual_beats):
        # Compile the visual beat into a WAN prompt
        try:
            wan_prompt = compile_wan_prompt(beat, topic_id, beat_idx)
        except VisualCompilationError as e:
            raise WanRenderError(
                f"Section {topic_id}, Beat {beat_idx}: Visual beat compilation failed. "
                f"Reason: {e.reason}"
            )
        
        # Generate output path for this beat
        beat_output_path = str(Path(output_dir) / f"topic_{topic_id}_beat_{beat_idx}.mp4")
        
        # Log the compiled prompt
        log_render_prompt(
            section_id=topic_id,
            section_title=f"{topic_title} - Beat {beat_idx}",
            renderer="wan_beat",
            prompt=wan_prompt,
            output_path=beat_output_path,
            extra_data={
                "section_type": section_type,
                "beat_index": beat_idx,
                "beat_total": len(visual_beats),
                "duration": beat_duration,
                "dry_run": dry_run,
                "skip_wan": skip_wan,
                "visual_beat_fields": list(beat.keys())
            },
            trace_output_dir=trace_output_dir
        )
        
        print(f"  [Beat {beat_idx}] Prompt: {wan_prompt[:80]}...")
        
        if dry_run:
            marker_path = beat_output_path.replace(".mp4", ".dry_run.txt")
            with open(marker_path, "w") as f:
                f.write(f"DRY RUN - Section {topic_id}, Beat {beat_idx}\n")
                f.write(f"Prompt: {wan_prompt}\n")
            video_paths.append(marker_path)
            continue
        
        if skip_wan:
            _create_beat_placeholder(beat_idx, topic_id, beat_output_path, beat_duration)
            video_paths.append(beat_output_path)
            continue
        
        # Generate actual video
        result_path = client.generate_video(
            prompt=wan_prompt,
            duration=beat_duration,
            output_path=beat_output_path
        )
        video_paths.append(result_path)
    
    print(f"[WAN] Completed {len(video_paths)} beat videos for section {topic_id}")
    
    # Return path to first beat (player will handle stitching or sequencing)
    return video_paths[0] if video_paths else None


def _create_beat_placeholder(beat_idx: int, topic_id: int, output_path: str, duration: int) -> str:
    """Create placeholder video for a single beat."""
    try:
        from moviepy import ColorClip
        
        # Different colors for different beats to show they're separate
        colors = [(30, 60, 90), (60, 30, 90), (90, 60, 30), (30, 90, 60), (60, 90, 30)]
        color = colors[beat_idx % len(colors)]
        
        bg = ColorClip(size=(1280, 720), color=color, duration=min(duration, 8))
        bg.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio=False,
            verbose=False,
            logger=None
        )
        bg.close()
        return output_path
        
    except Exception as e:
        print(f"Beat placeholder error: {e}")
        return _create_ffmpeg_placeholder(output_path, duration)


def _create_ffmpeg_placeholder(output_path: str, duration: int) -> str:
    """Fallback placeholder using ffmpeg."""
    import subprocess
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c=0x1e3c5a:s=1280x720:d={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        output_path
    ]
    subprocess.run(cmd, capture_output=True)
    return output_path


def _create_dry_run_placeholder(topic_id: int, output_path: str, duration: int) -> str:
    """Create a marker file for dry run mode."""
    marker_path = output_path.replace(".mp4", ".dry_run.txt")
    with open(marker_path, "w") as f:
        f.write(f"DRY RUN placeholder for topic {topic_id}\n")
        f.write(f"Duration: {duration}s\n")
        f.write(f"Output would be: {output_path}\n")
    print(f"[DRY RUN] Created marker: {marker_path}")
    return marker_path


def _create_placeholder_video(topic_id: int, topic_title: str, output_path: str, duration: int) -> str:
    """Create placeholder video when skip_wan is enabled."""
    try:
        from moviepy import ColorClip, TextClip, CompositeVideoClip
        
        bg = ColorClip(size=(1280, 720), color=(30, 60, 90), duration=min(duration, 10))
        
        try:
            txt = TextClip(
                text=f"Section {topic_id}: {topic_title[:40]}",
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
        return output_path
        
    except Exception as e:
        print(f"Placeholder error: {e}")
        return _create_ffmpeg_placeholder(output_path, duration)
