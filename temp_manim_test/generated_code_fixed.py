from manim import *

class MainScene(Scene):
    def construct(self):
        # Segment 1 (11.7s)
        # Create initial triangle
        A_coord = [-3, -2, 0]
        B_coord = [1, -2, 0]
        C_coord = [1, 1, 0]

        A = Dot(A_coord)
        B = Dot(B_coord)
        C = Dot(C_coord)

        line_AB = Line(A_coord, B_coord)
        line_BC = Line(B_coord, C_coord)
        line_CA = Line(C_coord, A_coord)

        triangle = VGroup(line_AB, line_BC, line_CA)

        label_A = Text("A", font_size=36).next_to(A, DL, buff=0.1)
        label_B = Text("B", font_size=36).next_to(B, DR, buff=0.1)
        label_C = Text("C", font_size=36).next_to(C, UP, buff=0.1)

        # Fixed: use move_to without alignment_point
        right_angle_square = Square(side_length=0.3, color=WHITE).move_to(B_coord).shift(RIGHT * 0.15 + UP * 0.15)

        angle_arc = Arc(radius=0.5, start_angle=0, angle=PI/4, arc_center=A_coord, color=YELLOW)
        angle_label = MathTex("A", font_size=36, color=YELLOW).next_to(angle_arc, DR, buff=0.1)

        initial_triangle_group = VGroup(triangle, label_A, label_B, label_C, right_angle_square, angle_arc, angle_label)
        self.play(Create(initial_triangle_group), run_time=2.0)
        self.wait(1.0)

        # Animation: subtle pulsing
        self.play(initial_triangle_group.animate.scale(1.05), run_time=1.5)
        self.play(initial_triangle_group.animate.scale(1/1.05), run_time=1.5)
        self.wait(2.0)
        self.play(Indicate(triangle, color=YELLOW), run_time=1.5)
        self.wait(1.7)
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        # Segment 1 (11.7s)

        # Segment 2 (27.4s)
        A_coord = [-3, -2, 0]
        B_coord = [1, -2, 0]
        C_coord = [1, 1, 0]

        line_AB = Line(A_coord, B_coord, color=YELLOW, stroke_width=6)
        line_BC = Line(B_coord, C_coord, color=YELLOW, stroke_width=6)
        line_CA = Line(C_coord, A_coord, color=YELLOW, stroke_width=6)

        triangle = VGroup(line_AB, line_BC, line_CA)

        label_A = Text("A", font_size=36).next_to(Dot(A_coord), DL, buff=0.1)
        label_B = Text("B", font_size=36).next_to(Dot(B_coord), DR, buff=0.1)
        label_C = Text("C", font_size=36).next_to(Dot(C_coord), UP, buff=0.1)

        right_angle_square = Square(side_length=0.3, color=WHITE).move_to(B_coord).shift(RIGHT * 0.15 + UP * 0.15)

        angle_arc = Arc(radius=0.5, start_angle=0, angle=PI/4, arc_center=A_coord, color=YELLOW)
        angle_label = MathTex("A", font_size=36, color=YELLOW).next_to(angle_arc, DR, buff=0.1)

        triangle_group = VGroup(triangle, label_A, label_B, label_C, right_angle_square, angle_arc, angle_label)
        self.play(Create(triangle_group), run_time=2.0)
        self.wait(1.0)

        # Hypotenuse - label BESIDE the line, not rotated
        hyp_label = Text("Hypotenuse", font_size=36, color=BLUE).next_to(line_CA.get_center(), UR, buff=0.3)
        self.play(
            line_CA.animate.set_color(BLUE),
            Write(hyp_label),
            run_time=2.0
        )
        self.play(Indicate(line_CA), run_time=1.0)
        self.wait(2.0)

        # Opposite side
        opp_label = Text("Opposite side", font_size=36, color=RED).next_to(line_BC.get_center(), RIGHT, buff=0.3)
        self.play(
            line_CA.animate.set_color(YELLOW),
            FadeOut(hyp_label),
            line_BC.animate.set_color(RED),
            Write(opp_label),
            run_time=2.0
        )
        self.play(Indicate(line_BC), run_time=1.0)
        self.wait(2.0)

        # Adjacent side
        adj_label = Text("Adjacent side", font_size=36, color=GREEN).next_to(line_AB.get_center(), DOWN, buff=0.3)
        self.play(
            line_BC.animate.set_color(YELLOW),
            FadeOut(opp_label),
            line_AB.animate.set_color(GREEN),
            Write(adj_label),
            run_time=2.0
        )
        self.play(Indicate(line_AB), run_time=1.0)
        self.wait(4.0)
        self.play(Circumscribe(triangle), run_time=2.0)
        self.wait(3.9)
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        # Segment 2 (27.4s)

        # Segment 3 (23.9s)
        A_coord = [-3, -2, 0]
        B_coord = [1, -2, 0]
        C_coord = [1, 1, 0]

        line_AB = Line(A_coord, B_coord, color=YELLOW, stroke_width=6)
        line_BC = Line(B_coord, C_coord, color=YELLOW, stroke_width=6)
        line_CA = Line(C_coord, A_coord, color=YELLOW, stroke_width=6)

        triangle = VGroup(line_AB, line_BC, line_CA)

        label_A = Text("A", font_size=36).next_to(Dot(A_coord), DL, buff=0.1)
        label_B = Text("B", font_size=36).next_to(Dot(B_coord), DR, buff=0.1)
        label_C = Text("C", font_size=36).next_to(Dot(C_coord), UP, buff=0.1)

        right_angle_square = Square(side_length=0.3, color=WHITE).move_to(B_coord).shift(RIGHT * 0.15 + UP * 0.15)

        angle_arc = Arc(radius=0.5, start_angle=0, angle=PI/4, arc_center=A_coord, color=YELLOW)
        angle_label = MathTex("A", font_size=36, color=YELLOW).next_to(angle_arc, DR, buff=0.1)

        triangle_group = VGroup(triangle, label_A, label_B, label_C, right_angle_square, angle_arc, angle_label)
        self.play(Create(triangle_group), run_time=1.0)
        self.wait(0.5)

        # Sin A
        sin_formula = MathTex(r"\text{Sin A} = \frac{\text{Opposite}}{\text{Hypotenuse}}").to_edge(UP).shift(RIGHT*2)
        self.play(Write(sin_formula), run_time=1.5)
        self.wait(0.5)
        self.play(line_BC.animate.set_color(RED), run_time=0.5)
        self.play(Indicate(line_BC), run_time=0.5)
        self.play(line_CA.animate.set_color(BLUE), run_time=0.5)
        self.play(Indicate(line_CA), run_time=0.5)
        self.play(line_BC.animate.set_color(YELLOW), line_CA.animate.set_color(YELLOW), run_time=0.5)
        self.wait(1.0)

        # Cos A
        cos_formula = MathTex(r"\text{Cos A} = \frac{\text{Adjacent}}{\text{Hypotenuse}}").next_to(sin_formula, DOWN, buff=0.5)
        self.play(Write(cos_formula), run_time=1.5)
        self.wait(0.5)
        self.play(line_AB.animate.set_color(GREEN), run_time=0.5)
        self.play(Indicate(line_AB), run_time=0.5)
        self.play(line_CA.animate.set_color(BLUE), run_time=0.5)
        self.play(Indicate(line_CA), run_time=0.5)
        self.play(line_AB.animate.set_color(YELLOW), line_CA.animate.set_color(YELLOW), run_time=0.5)
        self.wait(1.0)

        # Tan A
        tan_formula = MathTex(r"\text{Tan A} = \frac{\text{Opposite}}{\text{Adjacent}}").next_to(cos_formula, DOWN, buff=0.5)
        self.play(Write(tan_formula), run_time=1.5)
        self.wait(0.5)
        self.play(line_BC.animate.set_color(RED), run_time=0.5)
        self.play(Indicate(line_BC), run_time=0.5)
        self.play(line_AB.animate.set_color(GREEN), run_time=0.5)
        self.play(Indicate(line_AB), run_time=0.5)
        self.play(line_BC.animate.set_color(YELLOW), line_AB.animate.set_color(YELLOW), run_time=0.5)
        self.wait(4.0)
        self.play(Circumscribe(VGroup(sin_formula, cos_formula, tan_formula)), run_time=1.5)
        self.wait(0.4)
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        # Segment 3 (23.9s)
