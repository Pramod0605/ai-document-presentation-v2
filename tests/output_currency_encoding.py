from manim import *

class MainScene(Scene):
    def construct(self):
        # Segment 1 (5.0s) - Price increase
        price_old = Text("Rs. 100").scale(1.2)
        arrow = Arrow(LEFT, RIGHT).next_to(price_old, RIGHT)
        price_new = Text("Rs. 150").scale(1.2).next_to(arrow, RIGHT)
        price_group = VGroup(price_old, arrow, price_new)
        price_group.move_to(ORIGIN)
        
        self.play(Write(price_old), run_time=1.5)
        self.play(
            Create(arrow),
            Write(price_new),
            price_old.animate.set_color(RED),
            run_time=2.0
        )
        self.wait(1.5)

        # Segment 2 (5.0s) - Impact on savings
        self.play(FadeOut(price_group), run_time=1.0)
        
        impact_text = Text("Impact on Savings:", color=BLUE).to_edge(UP)
        bullet1 = Text("- Reduced purchasing power").next_to(impact_text, DOWN, buff=0.5)
        bullet2 = Text("- Value erosion").next_to(bullet1, DOWN, buff=0.3)
        
        self.play(Write(impact_text), run_time=1.0)
        self.play(Write(bullet1), Write(bullet2), run_time=2.0)
        self.wait(1.0)