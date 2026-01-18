from manim import *

class MainScene(Scene):
    def construct(self):
        # Segment 1 (16.8s)
        title = Text("Trigonometry", font_size=60, color=BLUE)
        subtitle = Text("Measuring Heights Without Climbing", font_size=32)
        subtitle.next_to(title, DOWN, buff=0.5)
        
        self.play(Write(title), run_time=2.0)
        self.play(FadeIn(subtitle), run_time=1.5)
        self.wait(2.5)
        
        building = Rectangle(height=3.0, width=1.0, color=YELLOW, fill_opacity=0.3)
        building.shift(RIGHT * 3 + DOWN * 0.5)
        person = Dot(color=RED, radius=0.15)
        person.shift(LEFT * 2 + DOWN * 2)
        
        self.play(Create(building), FadeIn(person), run_time=2.0)
        self.wait(2.0)
        
        sight_line = DashedLine(person.get_center(), building.get_top(), color=GREEN)
        self.play(Create(sight_line), run_time=1.5)
        self.wait(2.0)
        
        self.play(Indicate(sight_line), run_time=1.0)
        self.wait(1.3)
        
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        self.wait(0.450)
        
        # Segment 2 (31.5s)
        header = Text("Triangle Relationships", font_size=48, color=GOLD)
        header.to_edge(UP)
        self.play(Write(header), run_time=2.0)
        self.wait(2.0)
        
        A = LEFT * 2.5 + DOWN * 1.5
        B = RIGHT * 2.5 + DOWN * 1.5
        C = RIGHT * 2.5 + UP * 1.5
        
        triangle = Polygon(A, B, C, color=WHITE)
        self.play(Create(triangle), run_time=2.5)
        self.wait(2.0)
        
        person_dot = Dot(A, color=RED, radius=0.12)
        base_dot = Dot(B, color=BLUE, radius=0.12)
        top_dot = Dot(C, color=GREEN, radius=0.12)
        
        person_label = Text("You", font_size=24)
        person_label.next_to(A, LEFT, buff=0.3)
        base_label = Text("Base", font_size=24)
        base_label.next_to(B, DOWN, buff=0.3)
        top_label = Text("Top", font_size=24)
        top_label.next_to(C, RIGHT, buff=0.3)
        
        self.play(
            FadeIn(person_dot), FadeIn(base_dot), FadeIn(top_dot),
            Write(person_label), Write(base_label), Write(top_label),
            run_time=2.5
        )
        self.wait(3.0)
        
        self.play(Indicate(triangle), run_time=1.5)
        self.wait(3.0)
        
        angle_arc = Arc(radius=0.5, start_angle=0, angle=PI/4, color=YELLOW)
        angle_arc.shift(A)
        angle_label = Text("angle", font_size=20)
        angle_label.next_to(angle_arc, UR, buff=0.2)
        
        self.play(Create(angle_arc), Write(angle_label), run_time=2.0)
        self.wait(3.0)
        
        self.play(Circumscribe(triangle), run_time=1.5)
        self.wait(4.0)
        
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        self.wait(1.980)
        
        # Segment 3 (37.6s)
        title3 = Text("Right-Angled Triangle", font_size=48, color=TEAL)
        title3.to_edge(UP)
        self.play(Write(title3), run_time=2.0)
        self.wait(2.0)
        
        P1 = LEFT * 2 + DOWN * 1
        P2 = RIGHT * 2 + DOWN * 1
        P3 = RIGHT * 2 + UP * 2
        
        rt_triangle = Polygon(P1, P2, P3, color=WHITE)
        self.play(Create(rt_triangle), run_time=2.5)
        self.wait(2.0)
        
        right_angle_marker = Square(side_length=0.3, color=YELLOW)
        right_angle_marker.move_to(P2)
        right_angle_marker.shift(UP * 0.15 + LEFT * 0.15)
        self.play(Create(right_angle_marker), run_time=1.0)
        self.wait(2.0)
        
        opp_line = Line(P2, P3, color=RED, stroke_width=6)
        self.play(Create(opp_line), run_time=1.5)
        opp_label = Text("Opposite", font_size=28, color=RED)
        opp_label.next_to(opp_line.get_center(), RIGHT, buff=0.4)
        self.play(Write(opp_label), run_time=1.0)
        self.wait(2.5)
        
        adj_line = Line(P1, P2, color=GREEN, stroke_width=6)
        self.play(Create(adj_line), run_time=1.5)
        adj_label = Text("Adjacent", font_size=28, color=GREEN)
        adj_label.next_to(adj_line.get_center(), DOWN, buff=0.3)
        self.play(Write(adj_label), run_time=1.0)
        self.wait(2.5)
        
        hyp_line = Line(P1, P3, color=BLUE, stroke_width=6)
        self.play(Create(hyp_line), run_time=1.5)
        hyp_label = Text("Hypotenuse", font_size=28, color=BLUE)
        hyp_label.next_to(hyp_line.get_center(), UL, buff=0.4)
        self.play(Write(hyp_label), run_time=1.0)
        self.wait(3.0)
        
        self.play(Indicate(hyp_label), run_time=1.0)
        self.wait(4.0)
        
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        self.wait(5.070)
        
        # Segment 4 (17.3s)
        title4 = Text("Labeling the Sides", font_size=44, color=PURPLE)
        title4.to_edge(UP)
        self.play(Write(title4), run_time=1.5)
        self.wait(1.5)
        
        Q1 = LEFT * 2.5 + DOWN * 1
        Q2 = RIGHT * 1.5 + DOWN * 1
        Q3 = RIGHT * 1.5 + UP * 2
        
        tri2 = Polygon(Q1, Q2, Q3, color=WHITE)
        self.play(Create(tri2), run_time=2.0)
        self.wait(1.5)
        
        angle_marker = Arc(radius=0.4, start_angle=0, angle=0.7, color=YELLOW)
        angle_marker.shift(Q1)
        theta_label = MathTex(r"\theta", font_size=36, color=YELLOW)
        theta_label.next_to(angle_marker, RIGHT, buff=0.2)
        self.play(Create(angle_marker), Write(theta_label), run_time=1.5)
        self.wait(1.5)
        
        opp_text = Text("Opp", font_size=24, color=RED)
        opp_text.next_to(Line(Q2, Q3).get_center(), RIGHT, buff=0.3)
        adj_text = Text("Adj", font_size=24, color=GREEN)
        adj_text.next_to(Line(Q1, Q2).get_center(), DOWN, buff=0.3)
        hyp_text = Text("Hyp", font_size=24, color=BLUE)
        hyp_text.next_to(Line(Q1, Q3).get_center(), UL, buff=0.3)
        
        self.play(Write(opp_text), Write(adj_text), Write(hyp_text), run_time=2.0)
        self.wait(2.0)
        
        self.play(Indicate(hyp_text), run_time=1.0)
        self.wait(2.3)
        
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        
        # Segment 5 (11.7s)
        title5 = Text("Six Trigonometric Ratios", font_size=48, color=ORANGE)
        self.play(Write(title5), run_time=2.0)
        self.wait(1.5)
        
        ratios = VGroup(
            Text("Sine", font_size=32),
            Text("Cosine", font_size=32),
            Text("Tangent", font_size=32),
            Text("Cosecant", font_size=32),
            Text("Secant", font_size=32),
            Text("Cotangent", font_size=32)
        ).arrange(DOWN, buff=0.4)
        
        self.play(Write(ratios), run_time=4.0)
        self.wait(2.0)
        
        self.play(Indicate(ratios), run_time=1.2)
        self.wait(0.5)
        
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        
        # Segment 6 (32.0s)
        title6 = Text("Ratio Definitions", font_size=44, color=GOLD)
        title6.to_edge(UP)
        self.play(Write(title6), run_time=1.5)
        self.wait(1.5)
        
        sin_formula = MathTex(r"\sin A = \frac{\text{Opposite}}{\text{Hypotenuse}}", font_size=40)
        sin_formula.shift(UP * 1.5)
        self.play(Write(sin_formula), run_time=2.5)
        self.wait(2.5)
        
        cos_formula = MathTex(r"\cos A = \frac{\text{Adjacent}}{\text{Hypotenuse}}", font_size=40)
        cos_formula.next_to(sin_formula, DOWN, buff=0.5)
        self.play(Write(cos_formula), run_time=2.5)
        self.wait(2.5)
        
        tan_formula = MathTex(r"\tan A = \frac{\text{Opposite}}{\text{Adjacent}}", font_size=40)
        tan_formula.next_to(cos_formula, DOWN, buff=0.5)
        self.play(Write(tan_formula), run_time=2.5)
        self.wait(2.5)
        
        self.play(Indicate(sin_formula), run_time=1.0)
        self.wait(2.0)
        
        reciprocal_text = Text("Reciprocals: cosec, sec, cot", font_size=32, color=YELLOW)
        reciprocal_text.to_edge(DOWN)
        self.play(Write(reciprocal_text), run_time=2.0)
        self.wait(3.0)
        
        self.play(Circumscribe(VGroup(sin_formula, cos_formula, tan_formula)), run_time=1.5)
        self.wait(3.0)
        
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        self.wait(0.980)
        
        # Segment 7 (9.1s)
        recap_title = Text("Six Key Ratios", font_size=52, color=TEAL)
        self.play(Write(recap_title), run_time=2.0)
        self.wait(1.0)
        
        ratio_list = Text(
            "sin, cos, tan\ncosec, sec, cot",
            font_size=36,
            line_spacing=1.5
        )
        ratio_list.next_to(recap_title, DOWN, buff=0.8)
        
        self.play(Write(ratio_list), run_time=2.5)
        self.wait(1.5)
        
        self.play(Indicate(ratio_list), run_time=1.1)
        
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        # Hard Sync: Injected wait to match audio (8.60s -> 9.14s)
        self.wait(0.540)
