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

self.play(Write(title), run_time=2)
self.play(Write(subtitle), run_time=2)
self.play(Create(triangle), run_time=2)
self.play(Write(label_A), Write(label_B), Write(label_C), run_time=2)
self.wait(11.8)

# Segment 2 (19.8-42.1s) - Tan A = 1 implication
tan_eq = MathTex(r"\tan A = \frac{BC}{AB} = 1").to_edge(LEFT).shift(UP)
implies = MathTex(r"\Rightarrow BC = AB").next_to(tan_eq, DOWN)

# Highlight equal sides
side_ab = Line(triangle.get_vertices()[0], triangle.get_vertices()[1], color=YELLOW)
side_bc = Line(triangle.get_vertices()[1], triangle.get_vertices()[2], color=YELLOW)

self.play(Write(tan_eq), run_time=3)
self.play(Write(implies), run_time=2)
self.play(
    ShowCreation(side_ab),
    ShowCreation(side_bc),
    run_time=2
)
self.wait(15.3)

# Segment 3 (42.1-65.5s) - Expression analysis
expr1 = MathTex(r"2\sin A \cos A").to_edge(RIGHT).shift(UP * 2)
expr2 = MathTex(r"= 2 \cdot \frac{BC}{AC} \cdot \frac{AB}{AC}").next_to(expr1, DOWN)
expr3 = MathTex(r"= \frac{2(BC \cdot AB)}{AC^2}").next_to(expr2, DOWN)

self.play(Write(expr1), run_time=2)
self.play(Write(expr2), run_time=3)
self.play(Write(expr3), run_time=2)
self.wait(16.4)

# Segment 4 (65.5-89.4s) - Pythagoras application
pythag = MathTex(r"AC^2 = AB^2 + BC^2").to_edge(RIGHT).shift(DOWN)
pythag2 = MathTex(r"= AB^2 + AB^2 = 2AB^2").next_to(pythag, DOWN)

self.play(Write(pythag), run_time=3)
self.play(Write(pythag2), run_time=3)
self.wait(17.9)

# Segment 5 (89.4-104.6s) - Final verification
final = MathTex(r"\therefore 2\sin A \cos A = \frac{2AB^2}{2AB^2} = 1").scale(1.2)
final.move_to(ORIGIN).shift(DOWN * 2)

self.play(Write(final), run_time=3)
box = SurroundingRectangle(final, color=GREEN)
self.play(Create(box), run_time=2)
self.wait(10.2)
