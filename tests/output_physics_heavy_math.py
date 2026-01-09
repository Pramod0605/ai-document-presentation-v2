from manim import *

class MainScene(Scene):
    def construct(self):
        # Segment 1 (5.0s) - Wave Function
        equation = MathTex(
            r"\Psi(x,t) = A e^{i(kx - \omega t)}"
        ).scale(1.2)
        
        title = Text("Wave Function", font_size=36).to_edge(UP)
        
        self.play(
            Write(title),
            Write(equation),
            run_time=3.0
        )
        self.wait(2.0)
        
        # Segment 2 (5.0s) - Probability Distribution
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[0, 1, 0.2],
            x_length=6,
            y_length=3,
        ).shift(DOWN)
        
        def gaussian(x):
            return np.exp(-(x**2)/2) / np.sqrt(2*np.pi)
            
        prob_curve = axes.plot(gaussian, color=BLUE)
        
        self.play(
            FadeOut(equation),
            Create(axes),
            Create(prob_curve),
            run_time=3.0
        )
        
        flattened_curve = axes.plot(
            lambda x: gaussian(x) * 0.5,
            color=BLUE
        )
        
        self.play(
            Transform(prob_curve, flattened_curve),
            run_time=1.0
        )
        self.wait(1.0)