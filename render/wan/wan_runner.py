from pathlib import Path
from .wan_client import WANClient
from render.render_trace import log_render_prompt

def render_wan_video(topic: dict, output_dir: str) -> str:
    client = WANClient()
    
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
        extra_data={"duration": duration}
    )
    
    result_path = client.generate_video(
        prompt=wan_prompt,
        duration=min(duration, 60),
        output_path=output_path
    )
    
    return result_path
