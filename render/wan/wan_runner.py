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
    topic_id = topic.get("section_id", topic.get("id", 1))
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
    
    # For recap sections, render each recap_scene as a separate video
    recap_scenes = topic.get("recap_scenes", [])
    if section_type == "recap" and recap_scenes:
        return _render_recap_scenes(
            topic_id=topic_id,
            topic_title=topic_title,
            recap_scenes=recap_scenes,
            output_dir=output_dir,
            dry_run=dry_run,
            skip_wan=skip_wan,
            trace_output_dir=trace_output_dir
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


def _render_recap_scenes(
    topic_id: int,
    topic_title: str,
    recap_scenes: list,
    output_dir: str,
    dry_run: bool,
    skip_wan: bool,
    trace_output_dir: str
) -> str:
    """
    Render each recap scene as a separate WAN video.
    
    Recap sections have exactly 5 scenes, each covering one key concept.
    Each scene has: concept_title, description, wan_prompt, narration
    
    Creates: recap_{topic_id}_scene_{1..5}.mp4
    Returns path to first video (player sequences all 5).
    """
    if not recap_scenes:
        raise WanRenderError(
            f"Section {topic_id}: Recap section has no recap_scenes. "
            f"LLM must generate exactly 5 recap scenes."
        )
    
    if len(recap_scenes) != 5:
        print(f"[WARN] Section {topic_id}: Expected 5 recap scenes, got {len(recap_scenes)}")
    
    print(f"[WAN] Rendering {len(recap_scenes)} recap scenes for section {topic_id}")
    
    video_paths = []
    client = WANClient() if not skip_wan and not dry_run else None
    scene_duration = 5  # Each recap scene is 5 seconds
    
    for scene_idx, scene in enumerate(recap_scenes):
        scene_num = scene.get("scene", scene_idx + 1)
        concept_title = scene.get("concept_title", f"Concept {scene_num}")
        wan_prompt = scene.get("wan_prompt", "")
        
        if not wan_prompt:
            raise WanRenderError(
                f"Section {topic_id}, Recap Scene {scene_num}: Missing wan_prompt. "
                f"Each recap scene must have a wan_prompt for video generation."
            )
        
        # Generate output path for this scene
        scene_output_path = str(Path(output_dir) / f"recap_{topic_id}_scene_{scene_num}.mp4")
        
        # Log the prompt
        log_render_prompt(
            section_id=topic_id,
            section_title=f"{topic_title} - Recap Scene {scene_num}: {concept_title}",
            renderer="wan_recap",
            prompt=wan_prompt,
            output_path=scene_output_path,
            extra_data={
                "section_type": "recap",
                "scene_number": scene_num,
                "scene_total": len(recap_scenes),
                "concept_title": concept_title,
                "duration": scene_duration,
                "dry_run": dry_run,
                "skip_wan": skip_wan
            },
            trace_output_dir=trace_output_dir
        )
        
        print(f"  [Recap Scene {scene_num}] {concept_title}: {wan_prompt[:60]}...")
        
        if dry_run:
            marker_path = scene_output_path.replace(".mp4", ".dry_run.txt")
            with open(marker_path, "w") as f:
                f.write(f"DRY RUN - Section {topic_id}, Recap Scene {scene_num}\n")
                f.write(f"Concept: {concept_title}\n")
                f.write(f"Prompt: {wan_prompt}\n")
            video_paths.append(marker_path)
            continue
        
        if skip_wan:
            _create_recap_placeholder(scene_num, topic_id, concept_title, scene_output_path, scene_duration)
            video_paths.append(scene_output_path)
            continue
        
        # Generate actual video
        result_path = client.generate_video(
            prompt=wan_prompt,
            duration=scene_duration,
            output_path=scene_output_path
        )
        video_paths.append(result_path)
    
    print(f"[WAN] Completed {len(video_paths)} recap scene videos for section {topic_id}")
    
    # Return path to first scene (player will sequence all 5)
    return video_paths[0] if video_paths else None


def _create_recap_placeholder(scene_num: int, topic_id: int, concept_title: str, output_path: str, duration: int) -> str:
    """Create placeholder video for a recap scene."""
    try:
        from moviepy import ColorClip, TextClip, CompositeVideoClip
        
        # Purple/blue gradient colors for recap scenes
        colors = [(60, 30, 90), (45, 45, 100), (30, 60, 90), (50, 40, 95), (40, 50, 90)]
        color = colors[(scene_num - 1) % len(colors)]
        
        bg = ColorClip(size=(1280, 720), color=color, duration=duration)
        
        try:
            txt = TextClip(
                text=f"Recap {scene_num}: {concept_title[:30]}",
                font_size=36,
                color="white",
                size=(1280, 720)
            )
            txt = txt.with_position("center").with_duration(duration)
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
        print(f"Recap placeholder error: {e}")
        return _create_ffmpeg_placeholder(output_path, duration)


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


def render_from_video_prompts(
    section: dict,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False
) -> list:
    """
    Render videos from pre-generated video_prompts (from LLM).
    
    This bypasses visual_beat compilation since video_prompts already contain
    the full prompt text ready for WAN generation.
    
    Args:
        section: Section dict with video_prompts array
        output_dir: Directory to save generated videos
        dry_run: If True, only create marker files
        skip_wan: If True, create placeholder videos instead of calling API
        
    Returns:
        List of paths to generated video files
    """
    section_id = section.get("section_id") or section.get("id", 1)
    section_type = section.get("section_type", "content")
    video_prompts = section.get("video_prompts", [])
    
    if not video_prompts:
        raise WanRenderError(f"Section {section_id}: No video_prompts available")
    
    print(f"[WAN] Rendering {len(video_prompts)} video prompts for section {section_id}")
    
    from pathlib import Path
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    client = WANClient() if not skip_wan and not dry_run else None
    video_paths = []
    
    for i, vp in enumerate(video_prompts):
        prompt = vp.get("prompt", "")
        duration = vp.get("duration_seconds", 8)
        beat_id = vp.get("beat_id", f"{section_id}_{i}")
        
        if not prompt:
            print(f"  [Beat {i}] SKIP: Empty prompt")
            continue
        
        if section_type == "recap":
            video_file = output_path / f"recap_{section_id}_scene_{i+1}.mp4"
        else:
            video_file = output_path / f"topic_{section_id}_beat_{i}.mp4"
        
        print(f"  [Beat {beat_id}] {len(prompt.split())} words, {duration}s")
        print(f"    Preview: {prompt[:80]}...")
        
        if dry_run:
            marker_path = str(video_file).replace(".mp4", ".dry_run.txt")
            with open(marker_path, "w") as f:
                f.write(f"DRY RUN - Section {section_id}, Beat {i}\n")
                f.write(f"Prompt: {prompt}\n")
            video_paths.append(marker_path)
            continue
        
        if skip_wan:
            _create_beat_placeholder(i, section_id, str(video_file), duration)
            video_paths.append(str(video_file))
            continue
        
        try:
            result_path = client.generate_video(
                prompt=prompt,
                duration=min(duration, 10),
                output_path=str(video_file)
            )
            video_paths.append(result_path)
        except Exception as e:
            print(f"  [Beat {beat_id}] ERROR: {e}")
            _create_beat_placeholder(i, section_id, str(video_file), duration)
            video_paths.append(str(video_file))
    
    print(f"[WAN] Completed {len(video_paths)} videos for section {section_id}")
    
    if video_paths and section_type != "recap":
        combined_path = output_path / f"topic_{section_id}.mp4"
        if len(video_paths) == 1:
            import shutil
            shutil.copy(video_paths[0], str(combined_path))
        else:
            _stitch_beat_videos(video_paths, str(combined_path))
        return [str(combined_path)] + video_paths
    
    return video_paths


def _stitch_beat_videos(video_paths: list, output_path: str) -> str:
    """Stitch multiple beat videos into a single video."""
    try:
        from moviepy import VideoFileClip, concatenate_videoclips
        
        clips = []
        for vp in video_paths:
            if vp.endswith('.mp4') and Path(vp).exists():
                clips.append(VideoFileClip(vp))
        
        if clips:
            final = concatenate_videoclips(clips)
            final.write_videofile(output_path, fps=24, codec="libx264", audio=False, verbose=False, logger=None)
            for c in clips:
                c.close()
            final.close()
            return output_path
    except Exception as e:
        print(f"Stitch error: {e}, returning first video")
    
    if video_paths:
        import shutil
        shutil.copy(video_paths[0], output_path)
    return output_path
