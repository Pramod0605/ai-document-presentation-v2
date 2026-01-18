from manim import *

class MainScene(Scene):
    def construct(self):
        # Segment 1 (11.7s)
        # Dark background is implicit
        A = [-3, -2, 0]
        B = [-3, 2, 0]
        C = [2, -2, 0]

        triangle = Polygon(A, B, C, color=WHITE, fill_opacity=0.2)
        right_angle_square = Square(side_length=0.3, color=WHITE).move_to(C, UL).shift(0.1 * DR)

        label_A = MathTex("A", font_size=36).next_to(A, DL)
        label_B = MathTex("B", font_size=36).next_to(B, UL)
        label_C = MathTex("C", font_size=36).next_to(C, DR)

        angle_arc = Arc(radius=0.5, start_angle=0, angle=np.arctan2(B[1]-A[1], B[0]-A[0]), arc_center=A, color=YELLOW)
        angle_label = MathTex("alpha", font_size=30, color=YELLOW).next_to(angle_arc, UR, buff=0.1)

        slider_line = Line(LEFT * 4 + UP * 2, LEFT * 4 + DOWN * 2, color=GRAY)
        slider_label = Text("Angle Size", font_size=24).next_to(slider_line, LEFT)
        slider_handle = Dot(slider_line.get_bottom(), color=BLUE)

        # Initial side lengths
        side_AC_val = MathTex("5.0", font_size=24).next_to(Line(A, C), DOWN, buff=0.1)
        side_BC_val = MathTex("4.0", font_size=24).next_to(Line(B, C), RIGHT, buff=0.1)

        self.play(
            Create(triangle),
            Write(label_A), Write(label_B), Write(label_C),
            Create(right_angle_square),
            Create(angle_arc), Write(angle_label),
            run_time=2.0
        )
        self.play(
            Create(slider_line),
            Write(slider_label),
            Create(slider_handle),
            run_time=1.0
        )
        self.wait(1.0)

        # Simulate angle change
        def update_triangle(mobject, alpha):
            new_angle_rad = interpolate(np.pi/4, np.pi/2.5, alpha) # From 45 to 72 degrees approx
            new_C_x = A[0] + (B[1] - A[1]) / np.tan(new_angle_rad)
            new_C = [new_C_x, A[1], 0]
            
            mobject.become(Polygon(A, B, new_C, color=WHITE, fill_opacity=0.2))
            label_C.next_to(new_C, DR)
            right_angle_square.move_to(new_C, UL).shift(0.1 * DR)
            angle_arc.become(Arc(radius=0.5, start_angle=0, angle=new_angle_rad, arc_center=A, color=YELLOW))
            angle_label.next_to(angle_arc, UR, buff=0.1)

            # Update side lengths
            len_AC = np.linalg.norm(np.array(A) - np.array(new_C))
            len_BC = np.linalg.norm(np.array(B) - np.array(new_C))
            side_AC_val.become(MathTex(f"{len_AC:.1f}", font_size=24).next_to(Line(A, new_C), DOWN, buff=0.1))
            side_BC_val.become(MathTex(f"{len_BC:.1f}", font_size=24).next_to(Line(B, new_C), RIGHT, buff=0.1))

        self.play(
            slider_handle.animate.move_to(slider_line.get_top()),
            # SKIPPED: UpdateFromAlphaFunc removed
            run_time=3.0
        )
        self.wait(1.0)
        self.play(
            slider_handle.animate.move_to(slider_line.get_bottom()),
            # SKIPPED: UpdateFromAlphaFunc removed
            run_time=3.0
        )
        self.wait(0.7)
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        # Segment 1 (11.7s)

        # Segment 2 (27.4s)
        # Triangle 1
        A1 = [-4, -2, 0]
        B1 = [-4, 2, 0]
        C1 = [-1, -2, 0]
        triangle1 = Polygon(A1, B1, C1, color=YELLOW, fill_opacity=0.3)
        right_angle_square1 = Square(side_length=0.3, color=WHITE).move_to(C1, UL).shift(0.1 * DR)
        label_A1 = MathTex("A", font_size=36).next_to(A1, DL)
        label_B1 = MathTex("B", font_size=36).next_to(B1, UL)
        label_C1 = MathTex("C", font_size=36).next_to(C1, DR)
        angle_arc1 = Arc(radius=0.5, start_angle=0, angle=np.arctan2(B1[1]-A1[1], B1[0]-A1[0]), arc_center=A1, color=YELLOW)
        triangle_label1 = Text("1", font_size=30).next_to(triangle1, UP)

        self.play(
            Create(triangle1),
            Create(right_angle_square1),
            Write(label_A1), Write(label_B1), Write(label_C1),
            Create(angle_arc1),
            Write(triangle_label1),
            run_time=2.0
        )
        self.wait(1.0)

        hypotenuse_line1 = Line(A1, B1)
        hypotenuse_label1 = Text("Hypotenuse", font_size=28).next_to(hypotenuse_line1, UP, buff=0.1)
        self.play(Write(hypotenuse_label1), run_time=2.0)
        self.wait(1.0)

        opposite_arrow1 = Arrow(start=A1 + RIGHT * 0.5, end=C1 + UP * 0.5, color=RED)
        opposite_label1 = Text("Opposite side", font_size=28).next_to(opposite_arrow1, RIGHT, buff=0.1)
        self.play(Create(opposite_arrow1), Write(opposite_label1), run_time=2.0)
        self.wait(1.0)

        adjacent_arrow1 = Arrow(start=A1 + UP * 0.5, end=C1 + LEFT * 0.5, color=BLUE)
        adjacent_label1 = Text("Adjacent side", font_size=28).next_to(adjacent_arrow1, DOWN, buff=0.1)
        self.play(Create(adjacent_arrow1), Write(adjacent_label1), run_time=2.0)
        self.wait(1.0)

        # Pan to Triangle 2
        A2 = [2, -2, 0]
        B2 = [2, 2, 0]
        C2 = [5, -2, 0]
        triangle2 = Polygon(A2, B2, C2, color=GREEN, fill_opacity=0.3)
        right_angle_square2 = Square(side_length=0.3, color=WHITE).move_to(C2, UL).shift(0.1 * DR)
        label_A2 = MathTex("A", font_size=36).next_to(A2, DL)
        label_B2 = MathTex("B", font_size=36).next_to(B2, UL)
        label_C2 = MathTex("C", font_size=36).next_to(C2, DR)
        angle_arc2 = Arc(radius=0.5, start_angle=0, angle=np.arctan2(B2[1]-A2[1], B2[0]-A2[0]), arc_center=A2, color=YELLOW)
        triangle_label2 = Text("2", font_size=30).next_to(triangle2, UP)

        self.play(
            self.camera.frame.animate.shift(RIGHT * 6),
            FadeOut(triangle1, right_angle_square1, label_A1, label_B1, label_C1, angle_arc1, triangle_label1,
                    hypotenuse_label1, opposite_arrow1, opposite_label1, adjacent_arrow1, adjacent_label1),
            FadeIn(triangle2, right_angle_square2, label_A2, label_B2, label_C2, angle_arc2, triangle_label2),
            run_time=2.0
        )
        self.wait(1.0)

        hypotenuse_line2 = Line(A2, B2)
        hypotenuse_label2 = Text("Hypotenuse", font_size=28).next_to(hypotenuse_line2, UP, buff=0.1)
        self.play(Write(hypotenuse_label2), run_time=2.0)
        self.wait(1.0)

        opposite_arrow2 = Arrow(start=A2 + RIGHT * 0.5, end=C2 + UP * 0.5, color=RED)
        opposite_label2 = Text("Opposite side", font_size=28).next_to(opposite_arrow2, RIGHT, buff=0.1)
        self.play(Create(opposite_arrow2), Write(opposite_label2), run_time=2.0)
        self.wait(1.0)

        adjacent_arrow2 = Arrow(start=A2 + UP * 0.5, end=C2 + LEFT * 0.5, color=BLUE)
        adjacent_label2 = Text("Adjacent side", font_size=28).next_to(adjacent_arrow2, DOWN, buff=0.1)
        self.play(Create(adjacent_arrow2), Write(adjacent_label2), run_time=2.0)
        self.wait(1.0)
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        # Segment 2 (27.4s)

        # Segment 3 (23.9s)
        self.camera.frame.move_to(ORIGIN) # Reset camera position

        A = [-3, -2, 0]
        B = [-3, 2, 0]
        C = [1, -2, 0]
        triangle = Polygon(A, B, C, color=YELLOW, fill_opacity=0.3)
        right_angle_square = Square(side_length=0.3, color=WHITE).move_to(C, UL).shift(0.1 * DR)
        label_A = MathTex("A", font_size=36).next_to(A, DL)
        label_B = MathTex("B", font_size=36).next_to(B, UL)
        label_C = MathTex("C", font_size=36).next_to(C, DR)
        angle_arc = Arc(radius=0.5, start_angle=0, angle=np.arctan2(B[1]-A[1], B[0]-A[0]), arc_center=A, color=YELLOW)

        hypotenuse_line = Line(A, B)
        opposite_line = Line(B, C)
        adjacent_line = Line(A, C)

        hypotenuse_label = Text("Hypotenuse", font_size=24).next_to(hypotenuse_line, UP, buff=0.1)
        opposite_label = Text("Opposite", font_size=24).next_to(opposite_line, RIGHT, buff=0.1)
        adjacent_label = Text("Adjacent", font_size=24).next_to(adjacent_line, DOWN, buff=0.1)

        self.add(triangle, right_angle_square, label_A, label_B, label_C, angle_arc,
                 hypotenuse_label, opposite_label, adjacent_label)
        self.wait(0.5)

        # Sin A
        sin_A_text = MathTex("sin A = ", font_size=48).to_edge(UP).shift(LEFT * 2)
        self.play(Write(sin_A_text), run_time=1.0)
        self.wait(0.5)

        opposite_glow = SurroundingRectangle(opposite_label, color=RED, buff=0.1)
        self.play(Create(opposite_glow), run_time=0.5)
        opposite_copy = opposite_label.copy().next_to(sin_A_text, RIGHT, buff=0.2)
        self.play(TransformFromCopy(opposite_label, opposite_copy), FadeOut(opposite_glow), run_time=1.0)
        self.wait(0.5)

        fraction_line = Line(LEFT * 0.5, RIGHT * 0.5).next_to(opposite_copy, DOWN, buff=0.1).align_to(opposite_copy, LEFT)
        self.play(Create(fraction_line), run_time=0.5)

        hypotenuse_glow = SurroundingRectangle(hypotenuse_label, color=BLUE, buff=0.1)
        self.play(Create(hypotenuse_glow), run_time=0.5)
        hypotenuse_copy = hypotenuse_label.copy().next_to(fraction_line, DOWN, buff=0.1).align_to(fraction_line, LEFT)
        self.play(TransformFromCopy(hypotenuse_label, hypotenuse_copy), FadeOut(hypotenuse_glow), run_time=1.0)
        self.wait(1.0)

        sin_ratio = VGroup(opposite_copy, fraction_line, hypotenuse_copy)
        self.play(sin_ratio.animate.shift(RIGHT * 1.5), run_time=1.0)
        self.wait(1.0)

        # Cos A
        cos_A_text = MathTex("cos A = ", font_size=48).next_to(sin_A_text, DOWN, buff=0.5).align_to(sin_A_text, LEFT)
        self.play(Write(cos_A_text), run_time=1.0)
        self.wait(0.5)

        adjacent_glow = SurroundingRectangle(adjacent_label, color=GREEN, buff=0.1)
        self.play(Create(adjacent_glow), run_time=0.5)
        adjacent_copy = adjacent_label.copy().next_to(cos_A_text, RIGHT, buff=0.2)
        self.play(TransformFromCopy(adjacent_label, adjacent_copy), FadeOut(adjacent_glow), run_time=1.0)
        self.wait(0.5)

        fraction_line_cos = Line(LEFT * 0.5, RIGHT * 0.5).next_to(adjacent_copy, DOWN, buff=0.1).align_to(adjacent_copy, LEFT)
        self.play(Create(fraction_line_cos), run_time=0.5)

        hypotenuse_glow = SurroundingRectangle(hypotenuse_label, color=BLUE, buff=0.1)
        self.play(Create(hypotenuse_glow), run_time=0.5)
        hypotenuse_copy_cos = hypotenuse_label.copy().next_to(fraction_line_cos, DOWN, buff=0.1).align_to(fraction_line_cos, LEFT)
        self.play(TransformFromCopy(hypotenuse_label, hypotenuse_copy_cos), FadeOut(hypotenuse_glow), run_time=1.0)
        self.wait(1.0)

        cos_ratio = VGroup(adjacent_copy, fraction_line_cos, hypotenuse_copy_cos)
        self.play(cos_ratio.animate.shift(RIGHT * 1.5), run_time=1.0)
        self.wait(1.0)

        # Tan A
        tan_A_text = MathTex("tan A = ", font_size=48).next_to(cos_A_text, DOWN, buff=0.5).align_to(cos_A_text, LEFT)
        self.play(Write(tan_A_text), run_time=1.0)
        self.wait(0.5)

        opposite_glow = SurroundingRectangle(opposite_label, color=RED, buff=0.1)
        self.play(Create(opposite_glow), run_time=0.5)
        opposite_copy_tan = opposite_label.copy().next_to(tan_A_text, RIGHT, buff=0.2)
        self.play(TransformFromCopy(opposite_label, opposite_copy_tan), FadeOut(opposite_glow), run_time=1.0)
        self.wait(0.5)

        fraction_line_tan = Line(LEFT * 0.5, RIGHT * 0.5).next_to(opposite_copy_tan, DOWN, buff=0.1).align_to(opposite_copy_tan, LEFT)
        self.play(Create(fraction_line_tan), run_time=0.5)

        adjacent_glow = SurroundingRectangle(adjacent_label, color=GREEN, buff=0.1)
        self.play(Create(adjacent_glow), run_time=0.5)
        adjacent_copy_tan = adjacent_label.copy().next_to(fraction_line_tan, DOWN, buff=0.1).align_to(fraction_line_tan, LEFT)
        self.play(TransformFromCopy(adjacent_label, adjacent_copy_tan), FadeOut(adjacent_glow), run_time=1.0)
        self.wait(1.0)

        tan_ratio = VGroup(opposite_copy_tan, fraction_line_tan, adjacent_copy_tan)
        self.play(tan_ratio.animate.shift(RIGHT * 1.5), run_time=1.0)
        self.wait(0.4)
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        # Segment 3 (23.9s)

        # Segment 4 (19.3s)
        A_pt = [-3, -2, 0]
        B_pt = [-3, 2, 0]
        C_pt = [1, -2, 0]

        triangle = Polygon(A_pt, B_pt, C_pt, color=WHITE)
        right_angle_square = Square(side_length=0.3, color=WHITE).move_to(C_pt, UL).shift(0.1 * DR)

        side_AC_label = MathTex("3", font_size=40).next_to(Line(A_pt, C_pt), DOWN, buff=0.1)
        side_BC_label = MathTex("4", font_size=40).next_to(Line(B_pt, C_pt), RIGHT, buff=0.1)
        hyp_line_dashed = DashedLine(A_pt, B_pt, color=YELLOW)
        hyp_question = MathTex("?", font_size=40).next_to(hyp_line_dashed, UP, buff=0.1)

        self.play(
            Create(triangle),
            Create(right_angle_square),
            Write(side_AC_label),
            Write(side_BC_label),
            Create(hyp_line_dashed),
            Write(hyp_question),
            run_time=2.0
        )
        self.wait(0.5)

        pythagoras_theorem = MathTex("AC^2 = AB^2 + BC^2", font_size=48).to_edge(UP)
        self.play(Write(pythagoras_theorem), run_time=1.5)
        self.wait(0.5)

        # Substitute values
        pythagoras_sub = MathTex("AC^2 = 3^2 + 4^2", font_size=48).move_to(pythagoras_theorem)
        self.play(
            TransformFromCopy(side_AC_label, pythagoras_sub.get_part_by_tex("3")),
            TransformFromCopy(side_BC_label, pythagoras_sub.get_part_by_tex("4")),
            Transform(pythagoras_theorem, pythagoras_sub),
            run_time=2.0
        )
        self.wait(0.5)

        # Calculate squares
        pythagoras_calc1 = MathTex("AC^2 = 9 + 16", font_size=48).move_to(pythagoras_theorem)
        self.play(
            pythagoras_sub.get_part_by_tex("3^2").animate.become(pythagoras_calc1.get_part_by_tex("9")),
            pythagoras_sub.get_part_by_tex("4^2").animate.become(pythagoras_calc1.get_part_by_tex("16")),
            run_time=1.5
        )
        self.wait(0.5)

        # Calculate sum
        pythagoras_calc2 = MathTex("AC^2 = 25", font_size=48).move_to(pythagoras_theorem)
        self.play(Transform(pythagoras_calc1, pythagoras_calc2), run_time=1.5)
        self.wait(0.5)

        # Square root
        pythagoras_final = MathTex("AC = 5", font_size=48).move_to(pythagoras_theorem)
        self.play(
            Transform(pythagoras_calc2, pythagoras_final),
            run_time=1.5
        )
        self.wait(0.5)

        # Move 5 to hypotenuse
        hyp_value = MathTex("5", font_size=40, color=YELLOW).move_to(hyp_question)
        self.play(
            TransformFromCopy(pythagoras_final.get_part_by_tex("5"), hyp_value),
            FadeOut(hyp_question),
            run_time=1.5
        )
        self.wait(1.0)
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        # Segment 4 (19.3s)

        # Segment 5 (18.3s)
        A_pt = [-3, -2, 0]
        B_pt = [-3, 2, 0]
        C_pt = [1, -2, 0]

        triangle = Polygon(A_pt, B_pt, C_pt, color=WHITE)
        right_angle_square = Square(side_length=0.3, color=WHITE).move_to(C_pt, UL).shift(0.1 * DR)

        side_AC_label = MathTex("3", font_size=40).next_to(Line(A_pt, C_pt), DOWN, buff=0.1)
        side_BC_label = MathTex("4", font_size=40).next_to(Line(B_pt, C_pt), RIGHT, buff=0.1)
        side_AB_label = MathTex("5", font_size=40).next_to(Line(A_pt, B_pt), UP, buff=0.1)

        self.add(triangle, right_angle_square, side_AC_label, side_BC_label, side_AB_label)
        self.wait(0.5)

        # sin A = 4/5
        sin_A_eq = MathTex("sin A = 4/5", font_size=48).to_edge(UP)
        self.play(Write(sin_A_eq), run_time=1.0)
        self.wait(0.5)

        glow_4 = SurroundingRectangle(side_BC_label, color=RED, buff=0.1)
        glow_5 = SurroundingRectangle(side_AB_label, color=BLUE, buff=0.1)
        self.play(Create(glow_4), Create(glow_5), run_time=1.0)
        self.wait(1.0)
        self.play(FadeOut(glow_4, glow_5), run_time=0.5)

        # cos A = 3/5
        cos_A_eq = MathTex("cos A = 3/5", font_size=48).next_to(sin_A_eq, DOWN, buff=0.5).align_to(sin_A_eq, LEFT)
        self.play(Write(cos_A_eq), run_time=1.0)
        self.wait(0.5)

        glow_3 = SurroundingRectangle(side_AC_label, color=GREEN, buff=0.1)
        glow_5_cos = SurroundingRectangle(side_AB_label, color=BLUE, buff=0.1)
        self.play(Create(glow_3), Create(glow_5_cos), run_time=1.0)
        self.wait(1.0)
        self.play(FadeOut(glow_3, glow_5_cos), run_time=0.5)

        # tan A = 4/3
        tan_A_eq = MathTex("tan A = 4/3", font_size=48).next_to(cos_A_eq, DOWN, buff=0.5).align_to(cos_A_eq, LEFT)
        self.play(Write(tan_A_eq), run_time=1.0)
        self.wait(0.5)

        glow_4_tan = SurroundingRectangle(side_BC_label, color=RED, buff=0.1)
        glow_3_tan = SurroundingRectangle(side_AC_label, color=GREEN, buff=0.1)
        self.play(Create(glow_4_tan), Create(glow_3_tan), run_time=1.0)
        self.wait(1.0)
        self.play(FadeOut(glow_4_tan, glow_3_tan), run_time=0.5)
        self.wait(0.3)
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        # Segment 5 (18.3s)

        # Segment 6 (27.4s)
        # Triangle ABC
        A_abc = [-5, -2, 0]
        B_abc = [-5, 2, 0]
        C_abc = [-2, -2, 0]
        triangle_abc = Polygon(A_abc, B_abc, C_abc, color=WHITE)
        label_A_abc = MathTex("A", font_size=30).next_to(A_abc, DL)
        label_B_abc = MathTex("B", font_size=30).next_to(B_abc, UL)
        label_C_abc = MathTex("C", font_size=30).next_to(C_abc, DR)
        right_angle_abc = Square(side_length=0.3, color=WHITE).move_to(C_abc, UL).shift(0.1 * DR)

        # Triangle PQR
        P_pqr = [1, -2, 0]
        Q_pqr = [1, 2, 0]
        R_pqr = [4, -2, 0]
        triangle_pqr = Polygon(P_pqr, Q_pqr, R_pqr, color=WHITE)
        label_P_pqr = MathTex("P", font_size=30).next_to(P_pqr, DL)
        label_Q_pqr = MathTex("Q", font_size=30).next_to(Q_pqr, UL)
        label_R_pqr = MathTex("R", font_size=30).next_to(R_pqr, DR)
        right_angle_pqr = Square(side_length=0.3, color=WHITE).move_to(R_pqr, UL).shift(0.1 * DR)

        self.play(
            Create(triangle_abc), Write(label_A_abc), Write(label_B_abc), Write(label_C_abc), Create(right_angle_abc),
            Create(triangle_pqr), Write(label_P_pqr), Write(label_Q_pqr), Write(label_R_pqr), Create(right_angle_pqr),
            run_time=2.0
        )
        self.wait(0.5)

        sin_eq = MathTex("sin B = sin Q", font_size=40).to_edge(UP)
        self.play(Write(sin_eq), run_time=1.0)
        self.wait(0.5)

        # (AC/AB) = (PR/PQ)
        ratio_eq = MathTex("(AC/AB) = (PR/PQ)", font_size=40).move_to(sin_eq)
        self.play(Transform(sin_eq, ratio_eq), run_time=1.5)
        self.wait(0.5)

        # (AC/PR) = (AB/PQ) = k
        k_eq = MathTex("(AC/PR) = (AB/PQ) = k", font_size=40).move_to(ratio_eq)
        self.play(Transform(ratio_eq, k_eq), run_time=1.5)
        self.wait(1.0)

        # Pythagoras for BC
        pyth_BC = MathTex("BC = sqrt(AB^2 - AC^2)", font_size=36).next_to(k_eq, DOWN, buff=0.5).align_to(k_eq, LEFT)
        self.play(Write(pyth_BC), run_time=1.5)
        self.wait(0.5)

        # Substitute k*PQ and k*PR
        sub_BC = MathTex("BC = sqrt((k \\cdot PQ)^2 - (k \\cdot PR)^2)", font_size=36).move_to(pyth_BC)
        self.play(Transform(pyth_BC, sub_BC), run_time=2.0)
        self.wait(0.5)

        # Factor out k^2
        factor_BC = MathTex("BC = sqrt(k^2 (PQ^2 - PR^2))", font_size=36).move_to(sub_BC)
        self.play(Transform(sub_BC, factor_BC), run_time=1.5)
        self.wait(0.5)

        # Bring k out of sqrt
        k_out_BC = MathTex("BC = k \\cdot sqrt(PQ^2 - PR^2)", font_size=36).move_to(factor_BC)
        self.play(Transform(factor_BC, k_out_BC), run_time=1.5)
        self.wait(1.0)

        # Form BC/QR
        ratio_BC_QR = MathTex("BC/QR = (k \\cdot sqrt(PQ^2 - PR^2)) / sqrt(PQ^2 - PR^2)", font_size=36).next_to(k_out_BC, DOWN, buff=0.5).align_to(k_out_BC, LEFT)
        self.play(Write(ratio_BC_QR), run_time=2.0)
        self.wait(1.0)

        # Cancel sqrt terms
        final_ratio_BC_QR = MathTex("BC/QR = k", font_size=36).move_to(ratio_BC_QR)
        self.play(
            FadeOut(ratio_BC_QR.get_part_by_tex("sqrt(PQ^2 - PR^2)) / sqrt(PQ^2 - PR^2)")),
            Transform(ratio_BC_QR, final_ratio_BC_QR),
            run_time=1.5
        )
        self.wait(1.0)
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        # Segment 6 (27.4s)

        # Segment 7 (27.4s)
        # Triangle ABC
        A_abc = [-5, -2, 0]
        B_abc = [-5, 2, 0]
        C_abc = [-2, -2, 0]
        triangle_abc = Polygon(A_abc, B_abc, C_abc, color=WHITE)
        label_A_abc = MathTex("A", font_size=30).next_to(A_abc, DL)
        label_B_abc = MathTex("B", font_size=30).next_to(B_abc, UL)
        label_C_abc = MathTex("C", font_size=30).next_to(C_abc, DR)
        right_angle_abc = Square(side_length=0.3, color=WHITE).move_to(C_abc, UL).shift(0.1 * DR)

        # Triangle PQR
        P_pqr = [1, -2, 0]
        Q_pqr = [1, 2, 0]
        R_pqr = [4, -2, 0]
        triangle_pqr = Polygon(P_pqr, Q_pqr, R_pqr, color=WHITE)
        label_P_pqr = MathTex("P", font_size=30).next_to(P_pqr, DL)
        label_Q_pqr = MathTex("Q", font_size=30).next_to(Q_pqr, UL)
        label_R_pqr = MathTex("R", font_size=30).next_to(R_pqr, DR)
        right_angle_pqr = Square(side_length=0.3, color=WHITE).move_to(R_pqr, UL).shift(0.1 * DR)

        self.add(triangle_abc, label_A_abc, label_B_abc, label_C_abc, right_angle_abc,
                 triangle_pqr, label_P_pqr, label_Q_pqr, label_R_pqr, right_angle_pqr)
        self.wait(0.5)

        final_proportionality = MathTex("(AC/PR) = (AB/PQ) = (BC/QR)", font_size=40).to_edge(UP)
        self.play(Write(final_proportionality), run_time=1.5)
        self.wait(1.0)

        similarity_text = MathTex("Therefore, \\triangle ABC \\sim \\triangle PQR", font_size=48).next_to(final_proportionality, DOWN, buff=0.5)
        self.play(FadeIn(similarity_text), run_time=1.5)
        self.wait(1.0)

        # Animate PQR superimposing on ABC
        # Calculate scale factor and shift for PQR to match ABC
        scale_factor = np.linalg.norm(np.array(B_abc) - np.array(A_abc)) / np.linalg.norm(np.array(Q_pqr) - np.array(P_pqr))
        
        # Create a group for PQR and its labels
        pqr_group = VGroup(triangle_pqr, label_P_pqr, label_Q_pqr, label_R_pqr, right_angle_pqr)

        self.play(
            pqr_group.animate.scale(scale_factor).move_to(triangle_abc.get_center()),
            run_time=3.0
        )
        self.wait(1.0)

        # Flash angles B and Q
        angle_B_arc = Arc(radius=0.5, start_angle=np.pi/2, angle=np.arctan2(A_abc[1]-B_abc[1], A_abc[0]-B_abc[0]) - np.pi/2, arc_center=B_abc, color=YELLOW)
        angle_Q_arc = Arc(radius=0.5, start_angle=np.pi/2, angle=np.arctan2(P_pqr[1]-Q_pqr[1], P_pqr[0]-Q_pqr[0]) - np.pi/2, arc_center=Q_pqr, color=YELLOW).scale(scale_factor).move_to(angle_B_arc)

        self.play(
            Indicate(angle_B_arc, scale_factor=1.5, color=YELLOW),
            Indicate(angle_Q_arc, scale_factor=1.5, color=YELLOW),
            run_time=2.0
        )
        self.wait(1.0)

        angle_eq = MathTex("angle B = angle Q", font_size=48).next_to(similarity_text, DOWN, buff=0.5)
        self.play(Write(angle_eq), run_time=1.5)
        self.wait(1.0)

        # Fade out the scaled PQR group and its labels
        self.play(
            FadeOut(pqr_group),
            FadeOut(angle_B_arc), FadeOut(angle_Q_arc),
            run_time=1.0
        )
        self.wait(0.4)
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        # Segment 7 (27.4s)