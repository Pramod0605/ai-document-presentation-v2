from manim import *

class MathTexVerification(Scene):
    def construct(self):
        title = Text("Manim Verification", color=BLUE)
        equation = MathTex(r"c^2 = a^2 + b^2", font_size=72)
        
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))
        
        self.play(Write(equation))
        self.wait(2)
        
        box = SurroundingRectangle(equation, color=YELLOW)
        self.play(Create(box))
        self.wait(2)
        
        self.play(FadeOut(title), FadeOut(equation), FadeOut(box))
