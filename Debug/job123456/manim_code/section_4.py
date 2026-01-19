from manim import *

class MainScene(Scene):
    def construct(self):
        # Segment 1 (16.2s)
        title = Text("Glucose Breakdown", font_size=40).to_edge(UP)
        self.play(Write(title), run_time=1.5)
        self.wait(1.0)
        
        glucose = Circle(radius=0.8, color=BLUE, fill_opacity=0.3)
        glucose_label = Text("Glucose", font_size=28).next_to(glucose, UP, buff=0.3)
        glucose_carbon = Text("(6 carbons)", font_size=20).next_to(glucose, DOWN, buff=0.3)
        glucose_group = VGroup(glucose, glucose_label, glucose_carbon).shift(LEFT * 3)
        
        self.play(FadeIn(glucose_group), run_time=1.5)
        self.wait(1.5)
        
        arrow = Arrow(LEFT * 1.5, RIGHT * 1.5, color=YELLOW, buff=0.2)
        cytoplasm_label = Text("Cytoplasm", font_size=24, color=GRAY).next_to(arrow, UP, buff=0.2)
        
        self.play(Create(arrow), Write(cytoplasm_label), run_time=1.5)
        self.wait(1.0)
        
        pyruvate1 = Circle(radius=0.5, color=GREEN, fill_opacity=0.3).shift(RIGHT * 3 + UP * 0.7)
        pyruvate2 = Circle(radius=0.5, color=GREEN, fill_opacity=0.3).shift(RIGHT * 3 + DOWN * 0.7)
        pyruvate_label = Text("Pyruvate", font_size=28).next_to(pyruvate1, UP, buff=0.3)
        pyruvate_carbon = Text("(3 carbons each)", font_size=20).next_to(pyruvate2, DOWN, buff=0.3)
        pyruvate_group = VGroup(pyruvate1, pyruvate2, pyruvate_label, pyruvate_carbon)
        
        self.play(FadeIn(pyruvate_group), run_time=1.5)
        self.wait(1.5)
        
        self.play(Indicate(pyruvate_group), run_time=1.5)
        self.wait(2.7)
        
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        
        # Hard Sync: Injected wait to match audio (15.70s -> 16.25s)
        self.wait(0.550)
        # Segment 2 (13.2s)
        pyruvate_s2 = Circle(radius=0.6, color=GREEN, fill_opacity=0.3)
        pyruvate_label_s2 = Text("Pyruvate", font_size=32).next_to(pyruvate_s2, UP, buff=0.3)
        pyruvate_center = VGroup(pyruvate_s2, pyruvate_label_s2)
        
        self.play(FadeIn(pyruvate_center), run_time=1.5)
        self.wait(1.0)
        
        road1 = Arrow(ORIGIN, LEFT * 2 + UP * 1.5, color=RED, buff=0.6)
        road2 = Arrow(ORIGIN, RIGHT * 2 + UP * 1.5, color=ORANGE, buff=0.6)
        road3 = Arrow(ORIGIN, DOWN * 2, color=BLUE, buff=0.6)
        
        self.play(Create(road1), run_time=1.0)
        self.wait(0.5)
        self.play(Create(road2), run_time=1.0)
        self.wait(0.5)
        self.play(Create(road3), run_time=1.0)
        self.wait(1.0)
        
        oxygen_label = Text("Oxygen decides the path", font_size=28, color=YELLOW).to_edge(DOWN)
        self.play(Write(oxygen_label), run_time=1.5)
        self.wait(1.5)
        
        self.play(Circumscribe(pyruvate_center, color=YELLOW), run_time=1.5)
        self.wait(1.2)
        
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        
        # Segment 3 (11.7s)
        yeast_title = Text("Yeast - No Oxygen", font_size=36, color=RED).to_edge(UP)
        self.play(Write(yeast_title), run_time=1.5)
        self.wait(0.5)
        
        pyruvate_s3 = Circle(radius=0.5, color=GREEN, fill_opacity=0.3).shift(LEFT * 3)
        pyruvate_label_s3 = Text("Pyruvate", font_size=24).next_to(pyruvate_s3, UP, buff=0.2)
        
        self.play(FadeIn(VGroup(pyruvate_s3, pyruvate_label_s3)), run_time=1.0)
        self.wait(0.5)
        
        arrow_s3 = Arrow(LEFT * 2, RIGHT * 1, color=YELLOW, buff=0.2)
        self.play(Create(arrow_s3), run_time=1.0)
        self.wait(0.5)
        
        ethanol = Circle(radius=0.4, color=PURPLE, fill_opacity=0.3).shift(RIGHT * 2.5 + UP * 0.6)
        ethanol_label = Text("Ethanol", font_size=22).next_to(ethanol, RIGHT, buff=0.2)
        co2 = Circle(radius=0.3, color=GRAY, fill_opacity=0.3).shift(RIGHT * 2.5 + DOWN * 0.6)
        co2_label = Text("CO2", font_size=22).next_to(co2, RIGHT, buff=0.2)
        
        self.play(FadeIn(VGroup(ethanol, ethanol_label, co2, co2_label)), run_time=1.5)
        self.wait(1.0)
        
        bread_text = Text("Bread dough rises!", font_size=28, color=GOLD).to_edge(DOWN)
        self.play(Write(bread_text), run_time=1.5)
        self.wait(1.5)
        
        self.play(Indicate(VGroup(ethanol, co2)), run_time=1.2)
        self.wait(0.5)
        
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        
        # Hard Sync WARNING: Animation exceeds audio by 1.02s
        # Segment 4 (14.2s)
        muscle_title = Text("Muscle Cells - Low Oxygen", font_size=36, color=ORANGE).to_edge(UP)
        self.play(Write(muscle_title), run_time=1.5)
        self.wait(0.5)
        
        pyruvate_s4 = Circle(radius=0.5, color=GREEN, fill_opacity=0.3).shift(LEFT * 3)
        pyruvate_label_s4 = Text("Pyruvate", font_size=24).next_to(pyruvate_s4, UP, buff=0.2)
        
        self.play(FadeIn(VGroup(pyruvate_s4, pyruvate_label_s4)), run_time=1.0)
        self.wait(0.5)
        
        arrow_s4 = Arrow(LEFT * 2, RIGHT * 1, color=YELLOW, buff=0.2)
        exercise_label = Text("Hard exercise", font_size=20, color=GRAY).next_to(arrow_s4, UP, buff=0.2)
        
        self.play(Create(arrow_s4), Write(exercise_label), run_time=1.5)
        self.wait(1.0)
        
        lactic = Circle(radius=0.5, color=RED, fill_opacity=0.3).shift(RIGHT * 3)
        lactic_label = Text("Lactic Acid", font_size=24).next_to(lactic, UP, buff=0.2)
        
        self.play(FadeIn(VGroup(lactic, lactic_label)), run_time=1.5)
        self.wait(1.0)
        
        sore_text = Text("Causes muscle soreness", font_size=28, color=RED).to_edge(DOWN)
        self.play(Write(sore_text), run_time=1.5)
        self.wait(1.5)
        
        self.play(Indicate(lactic), run_time=1.5)
        self.wait(1.2)
        
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        
        # Segment 5 (12.7s)
        oxygen_title = Text("With Oxygen Available", font_size=36, color=BLUE).to_edge(UP)
        self.play(Write(oxygen_title), run_time=1.5)
        self.wait(0.5)
        
        pyruvate_s5 = Circle(radius=0.5, color=GREEN, fill_opacity=0.3).shift(LEFT * 3)
        pyruvate_label_s5 = Text("Pyruvate", font_size=24).next_to(pyruvate_s5, UP, buff=0.2)
        
        self.play(FadeIn(VGroup(pyruvate_s5, pyruvate_label_s5)), run_time=1.0)
        self.wait(0.5)
        
        mito = Ellipse(width=2.5, height=1.5, color=PURPLE, fill_opacity=0.2).shift(RIGHT * 2)
        mito_label = Text("Mitochondria", font_size=20).next_to(mito, UP, buff=0.2)
        
        self.play(Create(mito), Write(mito_label), run_time=1.5)
        self.wait(0.5)
        
        arrow_s5 = Arrow(LEFT * 1.5, RIGHT * 0.5, color=YELLOW, buff=0.2)
        self.play(Create(arrow_s5), run_time=1.0)
        self.wait(0.5)
        
        products = Text("CO2 + H2O + Energy", font_size=26, color=GOLD).shift(RIGHT * 2)
        self.play(Write(products), run_time=1.5)
        self.wait(1.0)
        
        energy_text = Text("Huge energy release!", font_size=28, color=YELLOW).to_edge(DOWN)
        self.play(Write(energy_text), run_time=1.0)
        self.wait(1.0)
        
        self.play(Indicate(products), run_time=1.0)
        self.wait(0.7)
        
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        
        # Hard Sync WARNING: Animation exceeds audio by 1.01s
        # Segment 6 (11.2s)
        atp_title = Text("Energy Storage: ATP", font_size=40, color=GOLD).to_edge(UP)
        self.play(Write(atp_title), run_time=1.5)
        self.wait(0.5)
        
        energy_symbol = Circle(radius=0.4, color=YELLOW, fill_opacity=0.5)
        energy_label = Text("Energy", font_size=24).next_to(energy_symbol, UP, buff=0.2)
        energy_group = VGroup(energy_symbol, energy_label).shift(LEFT * 3)
        
        self.play(FadeIn(energy_group), run_time=1.0)
        self.wait(0.5)
        
        arrow_atp = Arrow(LEFT * 1.5, RIGHT * 1.5, color=GREEN, buff=0.2)
        capture_label = Text("Captured", font_size=20, color=GRAY).next_to(arrow_atp, UP, buff=0.2)
        
        self.play(Create(arrow_atp), Write(capture_label), run_time=1.5)
        self.wait(0.5)
        
        atp = Circle(radius=0.6, color=GREEN, fill_opacity=0.3).shift(RIGHT * 3)
        atp_label = Text("ATP", font_size=32, color=GREEN).move_to(atp.get_center())
        atp_group = VGroup(atp, atp_label)
        
        self.play(FadeIn(atp_group), run_time=1.5)
        self.wait(1.0)
        
        currency_text = Text("Energy currency of cells", font_size=28, color=GOLD).to_edge(DOWN)
        self.play(Write(currency_text), run_time=1.0)
        self.wait(0.5)
        
        self.play(Circumscribe(atp_group, color=GOLD), run_time=1.0)
        self.wait(0.7)
        
        self.play(FadeOut(*self.mobjects), run_time=0.5)
        # Hard Sync WARNING: Animation exceeds audio by 0.53s
        self.wait(0.1) # Terminal stabilizer