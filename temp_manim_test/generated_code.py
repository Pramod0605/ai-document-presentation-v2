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

        right_angle_square = Square(side_length=0.3, color=WHITE).move_to(B_coord, alignment_point=DL)
        right_angle_square.shift(RIGHT * 0.1 + UP * 0.1)

        angle_arc = Arc(radius=0.5, start_angle=line_AB.get_angle(), angle=line_CA.get_angle() - line_AB.get_angle(), arc_center=A_coord, color=YELLOW)
        angle_label = MathTex("A", font_size=36, color=YELLOW).next_to(angle_arc, DR, buff=0.1)

        initial_triangle_group = VGroup(triangle, label_A, label_B, label_C, right_angle_square, angle_arc, angle_label)
        self.play(Create(initial_triangle_group), run_time=2.0)
        self.wait(1.0)

        # Animation: Change angle and sides
        # Target coordinates for a slightly different triangle
        A_coord_new = [-3.5, -2, 0]
        B_coord_new = [1, -2, 0]
        C_coord_new = [1, 1.5, 0] # Make C move up

        line_AB_new = Line(A_coord_new, B_coord_new)
        line_BC_new = Line(B_coord_new, C_coord_new)
        line_CA_new = Line(C_coord_new, A_coord_new)

        triangle_new = VGroup(line_AB_new, line_BC_new, line_CA_new)

        label_A_new = Text("A", font_size=36).next_to(Dot(A_coord_new), DL, buff=0.1)
        label_B_new = Text("B", font_size=36).next_to(Dot(B_coord_new), DR, buff=0.1)
        label_C_new = Text("C", font_size=36).next_to(Dot(C_coord_new), UP, buff=0.1)

        right_angle_square_new = Square(side_length=0.3, color=WHITE).move_to(B_coord_new, alignment_point=DL)
        right_angle_square_new.shift(RIGHT * 0.1 + UP * 0.1)

        angle_arc_new = Arc(radius=0.5, start_angle=line_AB_new.get_angle(), angle=line_CA_new.get_angle() - line_AB_new.get_angle(), arc_center=A_coord_new, color=YELLOW)
        angle_label_new = MathTex("A", font_size=36, color=YELLOW).next_to(angle_arc_new, DR, buff=0.1)

        new_triangle_group = VGroup(triangle_new, label_A_new, label_B_new, label_C_new, right_angle_square_new, angle_arc_new, angle_label_new)

        self.play(
            Transform(initial_triangle_group, new_triangle_group),
            run_time=3.0
        )
        self.wait(1.0)

        # Transform back to original for next segment
        self.play(
            Transform(initial_triangle_group, VGroup(triangle, label_A, label_B, label_C, right_angle_square, angle_arc, angle_label)),
            run_time=2.0
        )
        self.wait(2.2) # 2.0 + 1.0 + 3.0 + 1.0 + 2.0 + 2.2 = 11.2s. Need 11.7s.
        self.play(FadeOut(*self.mobjects), run_time=0.5) # Total 11.7s

        # Segment 2 (27.4s)
        A_coord = [-3, -2, 0]
        B_coord = [1, -2, 0]
        C_coord = [1, 1, 0]

        line_AB = Line(A_coord, B_coord, color=YELLOW_A, stroke_width=6)
        line_BC = Line(B_coord, C_coord, color=YELLOW_A, stroke_width=6)
        line_CA = Line(C_coord, A_coord, color=YELLOW_A, stroke_width=6)

        triangle = VGroup(line_AB, line_BC, line_CA)

        label_A = Text("A", font_size=36).next_to(Dot(A_coord), DL, buff=0.1)
        label_B = Text("B", font_size=36).next_to(Dot(B_coord), DR, buff=0.1)
        label_C = Text("C", font_size=36).next_to(Dot(C_coord), UP, buff=0.1)

        right_angle_square = Square(side_length=0.3, color=WHITE).move_to(B_coord, alignment_point=DL)
        right_angle_square.shift(RIGHT * 0.1 + UP * 0.1)

        angle_arc = Arc(radius=0.5, start_angle=line_AB.get_angle(), angle=line_CA.get_angle() - line_AB.get_angle(), arc_center=A_coord, color=YELLOW)
        angle_label = MathTex("A", font_size=36, color=YELLOW).next_to(angle_arc, DR, buff=0.1)

        triangle_group = VGroup(triangle, label_A, label_B, label_C, right_angle_square, angle_arc, angle_label)
        self.play(Create(triangle_group), run_time=2.0)
        self.wait(1.0)

        # Hypotenuse
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
            line_CA.animate.set_color(YELLOW_A),
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
            line_BC.animate.set_color(YELLOW_A),
            FadeOut(opp_label),
            line_AB.animate.set_color(GREEN),
            Write(adj_label),
            run_time=2.0
        )
        self.play(Indicate(line_AB), run_time=1.0)
        self.wait(10.9) # 2.0+1.0+2.0+1.0+2.0+1.0+2.0+1.0+2.0+1.0+10.9 = 27.4s
        self.play(FadeOut(*self.mobjects), run_time=0.5)

        # Segment 3 (23.9s)
        A_coord = [-3, -2, 0]
        B_coord = [1, -2, 0]
        C_coord = [1, 1, 0]

        line_AB = Line(A_coord, B_coord, color=YELLOW_A, stroke_width=6)
        line_BC = Line(B_coord, C_coord, color=YELLOW_A, stroke_width=6)
        line_CA = Line(C_coord, A_coord, color=YELLOW_A, stroke_width=6)

        triangle = VGroup(line_AB, line_BC, line_CA)

        label_A = Text("A", font_size=36).next_to(Dot(A_coord), DL, buff=0.1)
        label_B = Text("B", font_size=36).next_to(Dot(B_coord), DR, buff=0.1)
        label_C = Text("C", font_size=36).next_to(Dot(C_coord), UP, buff=0.1)

        right_angle_square = Square(side_length=0.3, color=WHITE).move_to(B_coord, alignment_point=DL)
        right_angle_square.shift(RIGHT * 0.1 + UP * 0.1)

        angle_arc = Arc(radius=0.5, start_angle=line_AB.get_angle(), angle=line_CA.get_angle() - line_AB.get_angle(), arc_center=A_coord, color=YELLOW)
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
        self.play(line_BC.animate.set_color(YELLOW_A), line_CA.animate.set_color(YELLOW_A), run_time=0.5)
        self.wait(1.0)

        # Cos A
        cos_formula = MathTex(r"\text{Cos A} = \frac{\text{Adjacent}}{\text{Hypotenuse}}").next_to(sin_formula, DOWN, buff=0.5)
        self.play(Write(cos_formula), run_time=1.5)
        self.wait(0.5)
        self.play(line_AB.animate.set_color(GREEN), run_time=0.5)
        self.play(Indicate(line_AB), run_time=0.5)
        self.play(line_CA.animate.set_color(BLUE), run_time=0.5)
        self.play(Indicate(line_CA), run_time=0.5)
        self.play(line_AB.animate.set_color(YELLOW_A), line_CA.animate.set_color(YELLOW_A), run_time=0.5)
        self.wait(1.0)

        # Tan A
        tan_formula = MathTex(r"\text{Tan A} = \frac{\text{Opposite}}{\text{Adjacent}}").next_to(cos_formula, DOWN, buff=0.5)
        self.play(Write(tan_formula), run_time=1.5)
        self.wait(0.5)
        self.play(line_BC.animate.set_color(RED), run_time=0.5)
        self.play(Indicate(line_BC), run_time=0.5)
        self.play(line_AB.animate.set_color(GREEN), run_time=0.5)
        self.play(Indicate(line_AB), run_time=0.5)
        self.play(line_BC.animate.set_color(YELLOW_A), line_AB.animate.set_color(YELLOW_A), run_time=0.5)
        self.wait(6.4) # 1.0+0.5+1.5+0.5+0.5+0.5+0.5+0.5+0.5+1.0+1.5+0.5+0.5+0.5+0.5+0.5+0.5+1.0+1.5+0.5+0.5+0.5+0.5+0.5+0.5+6.4 = 23.9s
        self.play(FadeOut(*self.mobjects), run_time=0.5)