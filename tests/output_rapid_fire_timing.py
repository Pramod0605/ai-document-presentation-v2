from manim import *

class MainScene(Scene):
    def construct(self):
        # Segment 1 (2.0s) - Square
        square = Square(side_length=2.0)
        self.play(Create(square), run_time=1.0)
        self.play(FadeOut(square), run_time=0.5)
        self.wait(0.5)

        # Segment 2 (2.0s) - Circle
        circle = Circle(radius=1.0)
        self.play(Create(circle), run_time=1.0)
        self.play(FadeOut(circle), run_time=0.5)
        self.wait(0.5)

        # Segment 3 (2.0s) - Triangle 
        triangle = Triangle().scale(2)
        self.play(Create(triangle), run_time=1.0)
        self.play(FadeOut(triangle), run_time=0.5)
        self.wait(0.5)