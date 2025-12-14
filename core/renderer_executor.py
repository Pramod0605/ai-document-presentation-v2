import os
from pathlib import Path
from render.wan.wan_runner import render_wan_video
from render.manim.manim_runner import render_manim_video

def execute_renderer(topic: dict, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    
    renderer = topic.get("renderer", "wan_video")
    
    if renderer == "manim":
        return render_manim_video(topic, output_dir)
    else:
        return render_wan_video(topic, output_dir)

def render_all_topics(presentation: dict, output_dir: str) -> list:
    os.makedirs(output_dir, exist_ok=True)
    
    rendered_videos = []
    topics = presentation.get("topics", [])
    
    for topic in topics:
        topic_id = topic.get("id", 1)
        print(f"Rendering topic {topic_id}: {topic.get('title', 'Untitled')}")
        
        video_path = execute_renderer(topic, output_dir)
        
        rendered_videos.append({
            "topic_id": topic_id,
            "renderer": topic.get("renderer", "wan_video"),
            "video_path": video_path
        })
        
        print(f"  -> Rendered: {video_path}")
    
    return rendered_videos
