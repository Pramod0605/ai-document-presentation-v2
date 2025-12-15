import os
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
from render.render_trace import log_render_prompt

MANIM_TEMPLATES = {
    "equation": '''
from manim import *

class EquationScene(Scene):
    def construct(self):
        equation = MathTex(r"{equation}")
        equation.scale({scale})
        self.play(Write(equation), run_time=2)
        self.wait({wait_time})
''',
    "graph": '''
from manim import *

class GraphScene(Scene):
    def construct(self):
        axes = Axes(
            x_range=[{x_min}, {x_max}, 1],
            y_range=[{y_min}, {y_max}, 1],
            axis_config={{"include_numbers": True}}
        )
        graph = axes.plot(lambda x: {function}, color=BLUE)
        label = MathTex(r"{label}").next_to(graph, UP)
        
        self.play(Create(axes), run_time=1.5)
        self.play(Create(graph), run_time=2)
        self.play(Write(label), run_time=1)
        self.wait({wait_time})
''',
    "geometry": '''
from manim import *

class GeometryScene(Scene):
    def construct(self):
        shapes = VGroup()
        {shape_code}
        self.play(Create(shapes), run_time=2)
        self.wait({wait_time})
''',
    "derivation": '''
from manim import *

class DerivationScene(Scene):
    def construct(self):
        steps = [{steps}]
        current = None
        for i, step in enumerate(steps):
            tex = MathTex(step)
            if current:
                tex.next_to(current, DOWN, buff=0.5)
            self.play(Write(tex), run_time=1.5)
            current = tex
            self.wait(0.5)
        self.wait({wait_time})
'''
}

def render_manim_video(topic: dict, output_dir: str, dry_run: bool = False) -> str:
    topic_id = topic.get("id", 1)
    topic_title = topic.get("title", "Untitled")
    explanation_plan = topic.get("explanation_plan", {})
    manim_plan = explanation_plan.get("manim_plan", {})
    duration = topic.get("duration", 30)
    
    scene_type = manim_plan.get("scene_type", "equation")
    params = manim_plan.get("params", {})
    
    output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")
    
    # Log the manim plan before rendering
    log_render_prompt(
        section_id=topic_id,
        section_title=topic_title,
        renderer="manim",
        prompt=json.dumps(manim_plan, indent=2),
        output_path=output_path,
        extra_data={"scene_type": scene_type, "duration": duration, "dry_run": dry_run}
    )
    
    # Generate the scene code (for logging purposes even in dry run)
    template = MANIM_TEMPLATES.get(scene_type, MANIM_TEMPLATES["equation"])
    default_params = {
        "equation": r"E = mc^2",
        "scale": 1.5,
        "wait_time": max(1, duration - 5),
        "x_min": -5,
        "x_max": 5,
        "y_min": -5,
        "y_max": 5,
        "function": "x**2",
        "label": "f(x)",
        "shape_code": "shapes.add(Circle(radius=1, color=BLUE))",
        "steps": '["x + 1 = 3", "x = 3 - 1", "x = 2"]'
    }
    render_params = {**default_params, **params}
    
    try:
        scene_code = template.format(**render_params)
    except KeyError as e:
        print(f"Missing parameter {e}, using defaults")
        scene_code = template.format(**default_params)
    
    # Log the generated Manim code
    log_render_prompt(
        section_id=topic_id,
        section_title=f"{topic_title} (generated code)",
        renderer="manim_code",
        prompt=scene_code,
        output_path=output_path,
        extra_data={"scene_type": scene_type, "dry_run": dry_run}
    )
    
    # In dry_run mode, create a marker file instead of running Manim
    if dry_run:
        print(f"[DRY RUN] Skipping Manim render for topic {topic_id}")
        return _create_dry_run_marker(topic_id, output_path, duration)
    
    try:
        result = _execute_manim_render(scene_type, params, duration, output_path, topic_id, topic_title, scene_code)
        return result
    except Exception as e:
        print(f"Manim render failed: {e}, using placeholder")
        return _create_placeholder(topic, output_path, duration)

def _execute_manim_render(scene_type: str, params: dict, duration: int, output_path: str, 
                          topic_id: int = 0, topic_title: str = "", scene_code: str = None) -> str:
    if scene_code is None:
        template = MANIM_TEMPLATES.get(scene_type, MANIM_TEMPLATES["equation"])
        default_params = {
            "equation": r"E = mc^2",
            "scale": 1.5,
            "wait_time": max(1, duration - 5),
            "x_min": -5,
            "x_max": 5,
            "y_min": -5,
            "y_max": 5,
            "function": "x**2",
            "label": "f(x)",
            "shape_code": "shapes.add(Circle(radius=1, color=BLUE))",
            "steps": '["x + 1 = 3", "x = 3 - 1", "x = 2"]'
        }
        render_params = {**default_params, **params}
        try:
            scene_code = template.format(**render_params)
        except KeyError as e:
            print(f"Missing parameter {e}, using defaults")
            scene_code = template.format(**default_params)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        scene_file = Path(tmpdir) / "scene.py"
        with open(scene_file, "w") as f:
            f.write(scene_code)
        
        scene_class = {
            "equation": "EquationScene",
            "graph": "GraphScene",
            "geometry": "GeometryScene",
            "derivation": "DerivationScene"
        }.get(scene_type, "EquationScene")
        
        cmd = [
            "manim", "render",
            "-ql",
            "-o", "output.mp4",
            "--media_dir", tmpdir,
            str(scene_file),
            scene_class
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=tmpdir
            )
            
            if result.returncode == 0:
                media_path = Path(tmpdir) / "videos" / "scene" / "480p15"
                for video_file in media_path.glob("*.mp4"):
                    shutil.copy(video_file, output_path)
                    return output_path
        except subprocess.TimeoutExpired:
            print("Manim render timed out")
        except FileNotFoundError:
            print("Manim not installed, using placeholder")
        except Exception as e:
            print(f"Manim execution error: {e}")
    
    return _create_placeholder({"explanation_plan": {"manim_plan": {"params": params}}}, output_path, duration)

def _create_dry_run_marker(topic_id: int, output_path: str, duration: int) -> str:
    """Create a simple marker file for dry run mode (no actual video rendering)."""
    marker_path = output_path.replace(".mp4", ".dry_run.txt")
    with open(marker_path, "w") as f:
        f.write(f"DRY RUN placeholder for Manim topic {topic_id}\n")
        f.write(f"Duration: {duration}s\n")
        f.write(f"Output would be: {output_path}\n")
    print(f"[DRY RUN] Created marker file: {marker_path}")
    return marker_path

def _create_placeholder(topic: dict, output_path: str, duration: int) -> str:
    try:
        from moviepy import ColorClip, TextClip, CompositeVideoClip
        
        bg = ColorClip(size=(1280, 720), color=(20, 40, 80), duration=min(duration, 5))
        
        manim_plan = topic.get("explanation_plan", {}).get("manim_plan", {})
        text = manim_plan.get("params", {}).get("equation", "Mathematical Visualization")
        
        try:
            txt = TextClip(
                text=text,
                font_size=48,
                color="white",
                size=(1280, 720)
            )
            txt = txt.with_position("center").with_duration(min(duration, 5))
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
        from moviepy import ColorClip
        clip = ColorClip(size=(1280, 720), color=(30, 50, 100), duration=3)
        clip.write_videofile(output_path, fps=24, codec="libx264", audio=False, verbose=False, logger=None)
        clip.close()
        return output_path
