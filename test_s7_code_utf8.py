# Segment 1 (0-17.8s) - Introducing the triangle
title = Text("Example 3: Trigonometric Identities", font_size=36).to_edge(UP)
triangle = Polygon(
    np.array([-2, -1, 0]), 
    np.array([1, -1, 0]), 
    np.array([-2, 1, 0]),
    color=WHITE
)
labels = VGroup(
    MathTex("A").next_to(triangle.get_vertices()[2], UP),
    MathTex("B").next_to(triangle.get_vertices()[1], RIGHT),
    MathTex("C").next_to(triangle.get_vertices()[0], LEFT),
    MathTex("29").next_to(triangle.get_edges()[1], UP+RIGHT, buff=0.2),
    MathTex("21").next_to(triangle.get_edges()[0], RIGHT),
    MathTex(r"\theta").next_to(triangle.get_vertices()[1], DOWN+RIGHT, buff=0.3)
)
right_angle = Square(side_length=0.2).next_to(triangle.get_vertices()[0], UP+RIGHT, buff=0)

self.play(Write(title), run_time=2)
self.play(Create(triangle), run_time=2)
self.play(Create(right_angle), run_time=1)
self.play(Write(labels), run_time=3)
self.wait(9.8)

# Segment 2 (17.8-36.5s) - Finding AC using Pythagoras
pythag = VGroup(
    MathTex(r"AC = \sqrt{AB^2 - BC^2}"),
    MathTex(r"= \sqrt{29^2 - 21^2}")
).arrange(DOWN).next_to(triangle, RIGHT, buff=1)

self.play(Write(pythag[0]), run_time=3)
self.wait(7)
self.play(Write(pythag[1]), run_time=3)
self.wait(5.8)

# Segment 3 (36.5-48.2s) - Calculating AC
calculation = VGroup(
    MathTex(r"= \sqrt{841 - 441}"),
    MathTex(r"= \sqrt{400}"),
    MathTex(r"= 20")
).arrange(DOWN).next_to(pythag, RIGHT, buff=0.5)

self.play(Write(calculation), run_time=4)
ac_label = MathTex("20").next_to(triangle.get_edges()[2], LEFT, buff=0.2)
self.play(FadeIn(ac_label), run_time=2)
self.wait(5.7)

# Segment 4 (48.2-65.0s) - Writing trig ratios
trig_ratios = VGroup(
    MathTex(r"\sin \theta = \frac{\text{Opposite}}{\text{Hypotenuse}} = \frac{20}{29}"),
    MathTex(r"\cos \theta = \frac{\text{Adjacent}}{\text{Hypotenuse}} = \frac{21}{29}")
).arrange(DOWN, buff=0.5).next_to(calculation, DOWN, buff=1)

self.play(Write(trig_ratios[0]), run_time=4)
self.play(Write(trig_ratios[1]), run_time=4)
self.wait(8.8)

# Segment 5 (65.0-77.2s) - First identity
identity1 = VGroup(
    MathTex(r"\cos^2 \theta + \sin^2 \theta = (\frac{21}{29})^2 + (\frac{20}{29})^2"),
    MathTex(r"= \frac{441}{841} + \frac{400}{841} = \frac{841}{841} = 1")
).arrange(DOWN).next_to(trig_ratios, DOWN, buff=0.5)

self.play(Write(identity1), run_time=6)
self.play(Circumscribe(identity1[1][-1], color=YELLOW), run_time=2)
self.wait(4.2)

# Segment 6 (77.2-88.8s) - Second identity
identity2 = VGroup(
    MathTex(r"\cos^2 \theta - \sin^2 \theta = (\frac{21}{29})^2 - (\frac{20}{29})^2"),
    MathTex(r"= \frac{441-400}{841} = \frac{41}{841}")
).arrange(DOWN).next_to(identity1, DOWN, buff=0.5)

self.play(Write(identity2), run_time=6)
self.play(Circumscribe(identity2[1][-1], color=YELLOW), run_time=2)
self.wait(3.7)
