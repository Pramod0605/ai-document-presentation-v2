import os
import traceback
from pathlib import Path
from render.wan.wan_runner import render_wan_video
from render.manim.manim_runner import render_manim_video

def execute_renderer(topic: dict, output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    
    topic_id = topic.get("id", 1)
    renderer = topic.get("renderer", "wan_video")
    section_type = topic.get("section_type", "content")
    visual_beats = topic.get("visual_beats", [])
    
    if visual_beats:
        if "explanation_plan" not in topic:
            topic["explanation_plan"] = {}
        topic["explanation_plan"]["visual_beats"] = visual_beats
    
    result = {
        "topic_id": topic_id,
        "section_type": section_type,
        "renderer": renderer,
        "status": "pending",
        "video_path": None,
        "error": None,
        "visual_beats_used": len(visual_beats) if visual_beats else 0
    }
    
    try:
        if renderer == "manim":
            video_path = render_manim_video(topic, output_dir)
        else:
            video_path = render_wan_video(topic, output_dir)
        
        result["status"] = "success"
        result["video_path"] = video_path
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        print(f"Error rendering topic {topic_id}: {e}")
    
    return result

def render_all_topics(presentation: dict, output_dir: str) -> list:
    os.makedirs(output_dir, exist_ok=True)
    
    rendered_videos = []
    topics = presentation.get("sections", presentation.get("topics", []))
    success_count = 0
    fail_count = 0
    
    for topic in topics:
        topic_id = topic.get("id", 1)
        print(f"Rendering topic {topic_id}: {topic.get('title', 'Untitled')}")
        
        result = execute_renderer(topic, output_dir)
        rendered_videos.append(result)
        
        if result["status"] == "success":
            success_count += 1
            print(f"  -> Success: {result['video_path']}")
        else:
            fail_count += 1
            print(f"  -> Failed: {result['error']}")
    
    print(f"Rendering complete: {success_count} success, {fail_count} failed")
    return rendered_videos
