from manim import *
import numpy as np

class TestSection8(Scene):
    def construct(self):
        # Segment 1 (0-19.8s) - Introduction
        title = Text("Example 4: Right Triangle Identity").to_edge(UP)
        subtitle = MathTex(r"\text{If } \tan A = 1, \text{ verify that } 2\sin A \cos A = 1").next_to(title, DOWN)

        # Create right triangle
        triangle = Polygon(
            ORIGIN, RIGHT * 3, UP * 3,
            color=WHITE, fill_opacity=0.2
        )
        triangle.move_to(ORIGIN)

        # Labels
        label_A = MathTex("A").next_to(triangle.get_vertices()[2], UP+RIGHT)
        label_B = MathTex("B").next_to(triangle.get_vertices()[0], DOWN+LEFT)
        label_C = MathTex("C").next_to(triangle.get_vertices()[1], DOWN+RIGHT)

        self.play(Write(title), run_time=1)
        self.play(Write(subtitle), run_time=1)
        self.play(Create(triangle), run_time=1)
        self.play(Write(label_A), Write(label_B), Write(label_C), run_time=1)

        # Segment 2 (19.8-42.1s) - Tan A = 1 implication
        tan_eq = MathTex(r"\tan A = \frac{BC}{AB} = 1").to_edge(LEFT).shift(UP)
        implies = MathTex(r"\Rightarrow BC = AB").next_to(tan_eq, DOWN)

        # Highlight equal sides
        side_ab = Line(triangle.get_vertices()[0], triangle.get_vertices()[1], color=YELLOW)
        side_bc = Line(triangle.get_vertices()[1], triangle.get_vertices()[2], color=YELLOW)

        self.play(Write(tan_eq), run_time=1)
        self.play(Write(implies), run_time=1)
        # BUG: ShowCreation should be Create
        self.play(
            Create(side_ab),
            Create(side_bc),
            run_time=1
        )
