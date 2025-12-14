import os
import subprocess
import tempfile
import shutil
from pathlib import Path

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

def render_manim_video(topic: dict, output_dir: str) -> str:
    topic_id = topic.get("id", 1)
    explanation_plan = topic.get("explanation_plan", {})
    manim_plan = explanation_plan.get("manim_plan", {})
    duration = topic.get("duration", 30)
    
    scene_type = manim_plan.get("scene_type", "equation")
    params = manim_plan.get("params", {})
    
    output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")
    
    try:
        result = _execute_manim_render(scene_type, params, duration, output_path)
        return result
    except Exception as e:
        print(f"Manim render failed: {e}, using placeholder")
        return _create_placeholder(topic, output_path, duration)

def _execute_manim_render(scene_type: str, params: dict, duration: int, output_path: str) -> str:
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
    
    return _create_placeholder({"explanation_plan": {"manim_plan": {"params": render_params}}}, output_path, duration)

def _create_placeholder(topic: dict, output_path: str, duration: int) -> str:
    try:
        from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
        
        bg = ColorClip(size=(1280, 720), color=(20, 40, 80), duration=duration)
        
        manim_plan = topic.get("explanation_plan", {}).get("manim_plan", {})
        text = manim_plan.get("params", {}).get("equation", "Mathematical Visualization")
        
        try:
            txt = TextClip(
                text,
                fontsize=48,
                color="white"
            )
            txt = txt.set_position("center").set_duration(duration)
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
        from moviepy.editor import ColorClip
        clip = ColorClip(size=(1280, 720), color=(30, 50, 100), duration=duration)
        clip.write_videofile(output_path, fps=24, codec="libx264", audio=False, verbose=False, logger=None)
        clip.close()
        return output_path
