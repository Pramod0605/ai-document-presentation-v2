"""
Manim Video Runner - Generates mathematical animations from visual beats

CRITICAL: NO placeholder fallbacks. Fail if scene is generic.
Each visual beat should produce specific Manim code, not E=mc² defaults.
"""
import os
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
from render.render_trace import log_render_prompt


class ManimRenderError(Exception):
    """Raised when Manim rendering fails - NO fallback to placeholders."""
    pass


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

# Placeholder equations that indicate generic/fallback content
BANNED_PLACEHOLDER_EQUATIONS = [
    "E = mc^2",
    "E=mc^2",
    "e = mc^2",
    "a^2 + b^2 = c^2",
    "x + 1 = 3",
    "f(x) = x",
    "y = x",
    "Step 1",
    "Step 2",
]


def render_manim_video(topic: dict, output_dir: str, dry_run: bool = False, trace_output_dir: str = None) -> str:
    """
    Render Manim video for a section with visual beats.
    
    FAIL-FAST: No placeholder fallbacks. Raise ManimRenderError if:
    - No compiled_manim_plan available
    - Plan uses generic/placeholder equations
    - Manim execution fails
    
    Handles multi_beat plans by rendering first beat (TODO: stitch all beats).
    """
    topic_id = topic.get("id", 1)
    topic_title = topic.get("title", "Untitled")
    section_type = topic.get("section_type", "content")
    explanation_plan = topic.get("explanation_plan", {})
    visual_beats = topic.get("visual_beats", [])
    duration = topic.get("duration", 30)
    
    # Check for compiled Manim plan from visual_compiler
    compiled_manim_plan = explanation_plan.get("compiled_manim_plan")
    legacy_manim_plan = explanation_plan.get("manim_plan", {})
    
    # Use compiled plan if available, else legacy
    manim_plan = compiled_manim_plan or legacy_manim_plan
    
    if not manim_plan or not manim_plan.get("scene_type"):
        # Try to compile from visual beats directly
        if visual_beats:
            manim_plan = _compile_beats_to_manim_plan(visual_beats, topic_id)
        else:
            raise ManimRenderError(
                f"Section {topic_id}: No Manim plan available. "
                f"Manim sections must have visual_beats or explicit manim_plan."
            )
    
    scene_type = manim_plan.get("scene_type", "equation")
    
    # Handle multi_beat plans - extract first beat for rendering
    if scene_type == "multi_beat":
        beats = manim_plan.get("beats", [])
        if not beats:
            raise ManimRenderError(
                f"Section {topic_id}: multi_beat plan has no beats"
            )
        # Use first beat's scene_type and params
        first_beat = beats[0]
        scene_type = first_beat.get("scene_type", "equation")
        params = first_beat.get("params", {})
        print(f"[MANIM] Multi-beat plan: using first of {len(beats)} beats (scene_type={scene_type})")
    else:
        params = manim_plan.get("params", {})
    
    # FAIL-FAST: Check for placeholder/generic content
    _validate_not_placeholder(params, topic_id, topic_title)
    
    output_path = str(Path(output_dir) / f"topic_{topic_id}.mp4")
    
    log_render_prompt(
        section_id=topic_id,
        section_title=topic_title,
        renderer="manim",
        prompt=json.dumps(manim_plan, indent=2),
        output_path=output_path,
        extra_data={
            "section_type": section_type,
            "scene_type": scene_type,
            "duration": duration, 
            "dry_run": dry_run,
            "params": params,
            "from_compiled_plan": compiled_manim_plan is not None
        },
        trace_output_dir=trace_output_dir
    )
    
    # Generate scene code
    template = MANIM_TEMPLATES.get(scene_type, MANIM_TEMPLATES["equation"])
    
    # NO DEFAULT PARAMS - use what's provided or fail
    render_params = {
        "wait_time": max(1, duration - 5),
        **params
    }
    
    try:
        scene_code = template.format(**render_params)
    except KeyError as e:
        raise ManimRenderError(
            f"Section {topic_id}: Missing required Manim parameter: {e}. "
            f"Scene type '{scene_type}' requires specific parameters. "
            f"Provided: {list(params.keys())}"
        )
    
    # Log generated code
    log_render_prompt(
        section_id=topic_id,
        section_title=f"{topic_title} (generated code)",
        renderer="manim_code",
        prompt=scene_code,
        output_path=output_path,
        extra_data={"scene_type": scene_type, "dry_run": dry_run},
        trace_output_dir=trace_output_dir
    )
    
    if dry_run:
        print(f"[DRY RUN] Manim render for section {topic_id}")
        return _create_dry_run_marker(topic_id, output_path, duration, scene_code)
    
    # Execute Manim render - NO FALLBACK
    result = _execute_manim_render(
        scene_type=scene_type,
        params=params,
        duration=duration,
        output_path=output_path,
        topic_id=topic_id,
        scene_code=scene_code
    )
    
    if not result or not os.path.exists(result):
        raise ManimRenderError(
            f"Section {topic_id}: Manim render produced no output. "
            f"Check Manim installation and scene code."
        )
    
    return result


def _compile_beats_to_manim_plan(visual_beats: list, topic_id: int) -> dict:
    """Compile visual beats into a Manim plan."""
    from core.visual_compiler import compile_manim_plan, VisualCompilationError
    
    if not visual_beats:
        raise ManimRenderError(f"Section {topic_id}: No visual beats to compile")
    
    # For now, compile first beat (multi-beat Manim is complex)
    beat = visual_beats[0]
    
    try:
        plan = compile_manim_plan(beat, topic_id, 0)
        return plan
    except VisualCompilationError as e:
        raise ManimRenderError(
            f"Section {topic_id}: Visual beat compilation failed - {e.reason}"
        )


def _validate_not_placeholder(params: dict, topic_id: int, topic_title: str):
    """Fail if params contain placeholder/generic content."""
    
    equation = params.get("equation", "")
    steps = params.get("steps", "")
    shape_code = params.get("shape_code", "")
    
    # Check equation
    for banned in BANNED_PLACEHOLDER_EQUATIONS:
        if banned.lower() in equation.lower():
            raise ManimRenderError(
                f"Section {topic_id} '{topic_title}': Generic placeholder equation detected: '{equation}'. "
                f"LLM must generate specific equations based on the topic, not fallback defaults."
            )
    
    # Check steps
    for banned in BANNED_PLACEHOLDER_EQUATIONS:
        if banned.lower() in steps.lower():
            raise ManimRenderError(
                f"Section {topic_id} '{topic_title}': Generic placeholder steps detected: '{steps}'. "
                f"LLM must generate specific derivation steps."
            )
    
    # Check shape code
    if shape_code == "shapes.add(Circle(radius=1, color=BLUE))":
        raise ManimRenderError(
            f"Section {topic_id} '{topic_title}': Generic placeholder geometry detected. "
            f"LLM must generate specific shape code for this topic."
        )


def _execute_manim_render(
    scene_type: str, 
    params: dict, 
    duration: int, 
    output_path: str, 
    topic_id: int,
    scene_code: str
) -> str:
    """Execute Manim render - raises ManimRenderError on failure."""
    
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
            "-ql",  # Low quality for speed
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
            
            if result.returncode != 0:
                raise ManimRenderError(
                    f"Section {topic_id}: Manim execution failed. "
                    f"Return code: {result.returncode}. "
                    f"Stderr: {result.stderr[:500]}"
                )
            
            # Find output video
            media_path = Path(tmpdir) / "videos" / "scene" / "480p15"
            for video_file in media_path.glob("*.mp4"):
                shutil.copy(video_file, output_path)
                print(f"[MANIM] Generated: {output_path}")
                return output_path
            
            raise ManimRenderError(
                f"Section {topic_id}: Manim produced no video output in {media_path}"
            )
            
        except subprocess.TimeoutExpired:
            raise ManimRenderError(
                f"Section {topic_id}: Manim render timed out after 120s"
            )
        except FileNotFoundError:
            raise ManimRenderError(
                f"Section {topic_id}: Manim not installed or not in PATH"
            )


def _create_dry_run_marker(topic_id: int, output_path: str, duration: int, scene_code: str) -> str:
    """Create marker file for dry run mode with full scene code."""
    marker_path = output_path.replace(".mp4", ".dry_run.txt")
    with open(marker_path, "w") as f:
        f.write(f"DRY RUN - Manim section {topic_id}\n")
        f.write(f"Duration: {duration}s\n")
        f.write(f"Output would be: {output_path}\n")
        f.write(f"\n--- SCENE CODE ---\n")
        f.write(scene_code)
    print(f"[DRY RUN] Created marker: {marker_path}")
    return marker_path
