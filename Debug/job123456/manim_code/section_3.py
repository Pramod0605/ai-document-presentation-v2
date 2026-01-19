from manim import *

class MainScene(Scene):
    def construct(self):
        # Segment 1 (22.9s)
        title = Text("Respiration: Energy from Food", font_size=40, color=YELLOW)
        title.to_edge(UP)
        self.play(Write(title), run_time=2.0)
        self.wait(2.0)

        food_icon = Circle(radius=0.8, color=ORANGE, fill_opacity=0.7)
        food_label = Text("Food", font_size=28)
        food_label.next_to(food_icon, DOWN, buff=0.3)
        food_group = VGroup(food_icon, food_label).shift(LEFT * 3)

        self.play(FadeIn(food_group), run_time=1.5)
        self.wait(2.0)

        arrow = Arrow(LEFT * 1.5, RIGHT * 1.5, color=WHITE, buff=0.3)
        process_text = Text("Respiration", font_size=24, color=GREEN)
        process_text.next_to(arrow, UP, buff=0.2)

        self.play(Create(arrow), Write(process_text), run_time=2.0)
        self.wait(2.0)

        energy_icon = Star(n=5, outer_radius=0.8, color=YELLOW, fill_opacity=0.8)
        energy_label = Text("Usable Energy", font_size=28)
        energy_label.next_to(energy_icon, DOWN, buff=0.3)
        energy_group = VGroup(energy_icon, energy_label).shift(RIGHT * 3)

        self.play(FadeIn(energy_group), run_time=1.5)
        self.wait(2.0)

        analogy = Text("Like cooking raw spices into a dish", font_size=24, color=TEAL)
        analogy.to_edge(DOWN)
        self.play(Write(analogy), run_time=2.0)
        self.wait(3.4)

        self.play(FadeOut(*self.mobjects), run_time=0.5)
        self.wait(1.950)

        # Segment 2 (23.4s)
        title_s2 = Text("ATP: The Energy Currency", font_size=40, color=YELLOW)
        title_s2.to_edge(UP)
        self.play(Write(title_s2), run_time=2.0)
        self.wait(2.0)

        atp_box = Rectangle(width=3, height=1.5, color=GOLD, fill_opacity=0.3)
        atp_text = Text("ATP", font_size=36, color=GOLD)
        atp_label = Text("Adenosine Triphosphate", font_size=20)
        atp_label.next_to(atp_box, DOWN, buff=0.3)
        atp_group = VGroup(atp_box, atp_text, atp_label)

        self.play(Create(atp_box), Write(atp_text), run_time=2.0)
        self.play(Write(atp_label), run_time=1.5)
        self.wait(2.0)

        self.play(Indicate(atp_group, scale_factor=1.1), run_time=1.5)
        self.wait(2.0)

        analogy_s2 = Text("Like firecrackers - ready-to-use energy!", font_size=28, color=ORANGE)
        analogy_s2.to_edge(DOWN)
        self.play(Write(analogy_s2), run_time=2.0)
        self.wait(2.0)

        spark1 = Star(n=5, outer_radius=0.3, color=RED, fill_opacity=0.8).shift(UP * 0.5 + LEFT * 2)
        spark2 = Star(n=5, outer_radius=0.3, color=YELLOW, fill_opacity=0.8).shift(UP * 0.5 + RIGHT * 2)
        spark3 = Star(n=5, outer_radius=0.3, color=ORANGE, fill_opacity=0.8).shift(DOWN * 0.5)

        self.play(FadeIn(spark1, spark2, spark3), run_time=1.0)
        self.wait(3.4)

        self.play(FadeOut(*self.mobjects), run_time=0.5)
        self.wait(1.450)

        # Segment 3 (16.8s)
        title_s3 = Text("Energy for Everything", font_size=40, color=YELLOW)
        title_s3.to_edge(UP)
        self.play(Write(title_s3), run_time=2.0)
        self.wait(1.5)

        uses = VGroup(
            Text("- Growing taller", font_size=28),
            Text("- Moving muscles", font_size=28),
            Text("- Repairing injuries", font_size=28)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.5)

        self.play(Write(uses[0]), run_time=1.5)
        self.wait(1.5)
        self.play(Write(uses[1]), run_time=1.5)
        self.wait(1.5)
        self.play(Write(uses[2]), run_time=1.5)
        self.wait(2.0)

        self.play(Circumscribe(uses, color=GREEN), run_time=1.5)
        self.wait(2.3)

        self.play(FadeOut(*self.mobjects), run_time=0.5)

        # Hard Sync WARNING: Animation exceeds audio by 0.55s
        # Segment 4 (17.3s)
        title_s4 = Text("Two Types of Respiration", font_size=40, color=YELLOW)
        title_s4.to_edge(UP)
        self.play(Write(title_s4), run_time=2.0)
        self.wait(2.0)

        aerobic_box = Rectangle(width=3.5, height=2, color=BLUE, fill_opacity=0.2).shift(LEFT * 3)
        aerobic_title = Text("Aerobic", font_size=32, color=BLUE)
        aerobic_title.move_to(aerobic_box.get_top() + DOWN * 0.5)
        aerobic_desc = Text("With Oxygen", font_size=24)
        aerobic_desc.next_to(aerobic_title, DOWN, buff=0.3)

        self.play(Create(aerobic_box), Write(aerobic_title), run_time=2.0)
        self.play(Write(aerobic_desc), run_time=1.5)
        self.wait(1.5)

        anaerobic_box = Rectangle(width=3.5, height=2, color=RED, fill_opacity=0.2).shift(RIGHT * 3)
        anaerobic_title = Text("Anaerobic", font_size=32, color=RED)
        anaerobic_title.move_to(anaerobic_box.get_top() + DOWN * 0.5)
        anaerobic_desc = Text("Without Oxygen", font_size=24)
        anaerobic_desc.next_to(anaerobic_title, DOWN, buff=0.3)

        self.play(Create(anaerobic_box), Write(anaerobic_title), run_time=2.0)
        self.play(Write(anaerobic_desc), run_time=1.5)
        self.wait(2.8)

        self.play(FadeOut(*self.mobjects), run_time=0.5)
        self.wait(1.460)

        # Segment 5 (21.3s)
        title_s5 = Text("Comparing the Two Types", font_size=40, color=YELLOW)
        title_s5.to_edge(UP)
        self.play(Write(title_s5), run_time=2.0)
        self.wait(1.5)

        aerobic_info = VGroup(
            Text("Aerobic (with O2):", font_size=28, color=BLUE),
            Text("- High energy", font_size=24),
            Text("- CO2 + H2O", font_size=24)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3).shift(LEFT * 3)

        self.play(Write(aerobic_info[0]), run_time=1.5)
        self.wait(1.0)
        self.play(Write(aerobic_info[1]), run_time=1.0)
        self.play(Write(aerobic_info[2]), run_time=1.0)
        self.wait(2.0)

        anaerobic_info = VGroup(
            Text("Anaerobic (no O2):", font_size=28, color=RED),
            Text("- Low energy", font_size=24),
            Text("- Ethanol/Lactic acid", font_size=24)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3).shift(RIGHT * 3)

        self.play(Write(anaerobic_info[0]), run_time=1.5)
        self.wait(1.0)
        self.play(Write(anaerobic_info[1]), run_time=1.0)
        self.play(Write(anaerobic_info[2]), run_time=1.0)
        self.wait(2.0)

        self.play(Indicate(aerobic_info, color=BLUE), run_time=1.0)
        self.wait(2.8)

        self.play(FadeOut(*self.mobjects), run_time=0.5)
        self.wait(0.520)

        # Segment 6 (26.4s)
        title_s6 = Text("Breathing vs Respiration", font_size=40, color=YELLOW)
        title_s6.to_edge(UP)
        self.play(Write(title_s6), run_time=2.0)
        self.wait(2.0)

        confusion = Text("Common Confusion: They are NOT the same!", font_size=28, color=RED)
        confusion.next_to(title_s6, DOWN, buff=0.5)
        self.play(Write(confusion), run_time=2.0)
        self.wait(2.0)

        breathing_box = Rectangle(width=4, height=2.5, color=TEAL, fill_opacity=0.2).shift(LEFT * 3 + DOWN * 0.5)
        breathing_title = Text("Breathing", font_size=30, color=TEAL)
        breathing_title.move_to(breathing_box.get_top() + DOWN * 0.4)
        breathing_desc = Text("Fuel delivery", font_size=24)
        breathing_desc.next_to(breathing_title, DOWN, buff=0.3)

        self.play(Create(breathing_box), Write(breathing_title), run_time=2.0)
        self.play(Write(breathing_desc), run_time=1.5)
        self.wait(2.0)

        respiration_box = Rectangle(width=4, height=2.5, color=GREEN, fill_opacity=0.2).shift(RIGHT * 3 + DOWN * 0.5)
        respiration_title = Text("Respiration", font_size=30, color=GREEN)
        respiration_title.move_to(respiration_box.get_top() + DOWN * 0.4)
        respiration_desc = Text("Engine burning fuel", font_size=24)
        respiration_desc.next_to(respiration_title, DOWN, buff=0.3)

        self.play(Create(respiration_box), Write(respiration_title), run_time=2.0)
        self.play(Write(respiration_desc), run_time=1.5)
        self.wait(2.0)

        self.play(Circumscribe(respiration_box, color=GREEN), run_time=1.5)
        self.wait(3.4)

        self.play(FadeOut(*self.mobjects), run_time=0.5)
        self.wait(2.000)

        # Segment 7 (19.3s)
        title_s7 = Text("The Key Difference", font_size=40, color=YELLOW)
        title_s7.to_edge(UP)
        self.play(Write(title_s7), run_time=2.0)
        self.wait(2.0)

        breathing_def = VGroup(
            Text("Breathing:", font_size=32, color=TEAL),
            Text("Physical gas exchange", font_size=26),
            Text("O2 in, CO2 out", font_size=24)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3).shift(UP * 0.5)

        self.play(Write(breathing_def[0]), run_time=1.5)
        self.play(Write(breathing_def[1]), run_time=1.5)
        self.play(Write(breathing_def[2]), run_time=1.5)
        self.wait(2.0)

        respiration_def = VGroup(
            Text("Respiration:", font_size=32, color=GREEN),
            Text("Chemical process in cells", font_size=26),
            Text("Produces energy (ATP)", font_size=24)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3).shift(DOWN * 1.5)

        self.play(Write(respiration_def[0]), run_time=1.5)
        self.play(Write(respiration_def[1]), run_time=1.5)
        self.play(Write(respiration_def[2]), run_time=1.5)
        self.wait(2.3)

        self.play(FadeOut(*self.mobjects), run_time=0.5)
        self.wait(1.490)

        # Segment 8 (14.7s)
        title_s8 = Text("Breathing Supplies, Respiration Powers", font_size=36, color=YELLOW)
        title_s8.to_edge(UP)
        self.play(Write(title_s8), run_time=2.0)
        self.wait(2.0)

        oxygen_circle = Circle(radius=0.6, color=BLUE, fill_opacity=0.5)
        oxygen_text = Text("O2", font_size=28)
        oxygen_group = VGroup(oxygen_circle, oxygen_text).shift(LEFT * 4)

        self.play(FadeIn(oxygen_group), run_time=1.0)
        self.wait(1.0)

        arrow_s8 = Arrow(LEFT * 2.5, RIGHT * 2.5, color=WHITE, buff=0.3)
        supply_text = Text("Breathing supplies", font_size=24)
        supply_text.next_to(arrow_s8, UP, buff=0.2)

        self.play(Create(arrow_s8), Write(supply_text), run_time=1.5)
        self.wait(1.5)

        energy_burst = Star(n=8, outer_radius=1, color=YELLOW, fill_opacity=0.7).shift(RIGHT * 4)
        energy_text_s8 = Text("Energy!", font_size=28, color=GOLD)
        energy_text_s8.next_to(energy_burst, DOWN, buff=0.3)

        self.play(FadeIn(energy_burst), Write(energy_text_s8), run_time=1.5)
        self.wait(2.2)

        self.play(FadeOut(*self.mobjects), run_time=0.5)
        self.wait(1.520)

        # Segment 9 (21.3s)
        title_s9 = Text("Respiration Never Stops!", font_size=40, color=YELLOW)
        title_s9.to_edge(UP)
        self.play(Write(title_s9), run_time=2.0)
        self.wait(2.0)

        running = Text("Running a race", font_size=28).shift(UP * 1.5 + LEFT * 3)
        sleeping = Text("Deep asleep", font_size=28).shift(UP * 1.5 + RIGHT * 3)

        self.play(Write(running), run_time=1.5)
        self.wait(1.5)
        self.play(Write(sleeping), run_time=1.5)
        self.wait(2.0)

        arrow_down = Arrow(UP * 0.5, DOWN * 0.5, color=GREEN)
        always_text = Text("Always Respiring!", font_size=32, color=GREEN)
        always_text.next_to(arrow_down, DOWN, buff=0.3)

        self.play(Create(arrow_down), Write(always_text), run_time=2.0)
        self.wait(2.0)

        functions = VGroup(
            Text("Heart beating", font_size=24),
            Text("Brain functioning", font_size=24),
            Text("Cells working", font_size=24)
        ).arrange(DOWN, buff=0.3).shift(DOWN * 2)

        self.play(Write(functions), run_time=2.0)
        self.wait(2.0)

        self.play(Indicate(always_text, scale_factor=1.2), run_time=1.0)
        self.wait(1.8)

        self.play(FadeOut(*self.mobjects), run_time=0.5)

        # Segment 10 (9.1s)
        title_s10 = Text("Life Depends on Respiration", font_size=40, color=YELLOW)
        title_s10.to_edge(UP)
        self.play(Write(title_s10), run_time=2.0)
        self.wait(2.0)

        statement = Text("Without continuous energy supply,", font_size=30)
        statement2 = Text("life would simply stop.", font_size=30, color=RED)
        statement_group = VGroup(statement, statement2).arrange(DOWN, buff=0.4)

        self.play(Write(statement), run_time=2.0)
        self.wait(1.0)
        self.play(Write(statement2), run_time=1.5)
        self.wait(0.6)

        self.play(FadeOut(*self.mobjects), run_time=0.5)

        # Segment 11 (18.3s)
        title_s11 = Text("Glucose Breakdown Flowchart", font_size=38, color=YELLOW)
        title_s11.to_edge(UP)
        self.play(Write(title_s11), run_time=2.0)
        self.wait(1.5)

        exam_note = Text("IMPORTANT FOR EXAMS!", font_size=28, color=RED)
        exam_note.next_to(title_s11, DOWN, buff=0.3)
        self.play(Write(exam_note), run_time=1.5)
        self.wait(1.5)

        glucose_box = Rectangle(width=2.5, height=1, color=ORANGE, fill_opacity=0.3).shift(UP * 1.5)
        glucose_text = Text("Glucose", font_size=26)
        glucose_text.move_to(glucose_box)
        glucose_label = Text("(6-carbon)", font_size=20)
        glucose_label.next_to(glucose_box, DOWN, buff=0.2)

        self.play(Create(glucose_box), Write(glucose_text), run_time=2.0)
        self.play(Write(glucose_label), run_time=1.0)
        self.wait(1.5)

        self.play(Indicate(glucose_box, color=ORANGE), run_time=1.5)
        self.wait(1.5)

        journey_text = Text("The journey begins...", font_size=26, color=TEAL)
        journey_text.to_edge(DOWN)
        self.play(Write(journey_text), run_time=1.5)
        self.wait(2.3)

        self.play(FadeOut(*self.mobjects), run_time=0.5)

        # Segment 12 (35.5s)
        title_s12 = Text("Complete Breakdown Process", font_size=36, color=YELLOW)
        title_s12.to_edge(UP)
        self.play(Write(title_s12), run_time=2.0)
        self.wait(2.0)

        glucose_s12 = Rectangle(width=2, height=0.8, color=ORANGE, fill_opacity=0.3).shift(UP * 2.5)
        glucose_txt = Text("Glucose", font_size=24)
        glucose_txt.move_to(glucose_s12)

        self.play(Create(glucose_s12), Write(glucose_txt), run_time=1.5)
        self.wait(1.5)

        arrow1 = Arrow(UP * 1.8, UP * 0.8, color=WHITE, buff=0.1)
        cytoplasm_label = Text("Cytoplasm", font_size=20, color=TEAL)
        cytoplasm_label.next_to(arrow1, RIGHT, buff=0.3)

        self.play(Create(arrow1), Write(cytoplasm_label), run_time=1.5)
        self.wait(1.5)

        pyruvate_box = Rectangle(width=2, height=0.8, color=GREEN, fill_opacity=0.3).shift(UP * 0.3)
        pyruvate_txt = Text("Pyruvate", font_size=24)
        pyruvate_txt.move_to(pyruvate_box)
        pyruvate_label = Text("(3-carbon)", font_size=18)
        pyruvate_label.next_to(pyruvate_box, DOWN, buff=0.15)

        self.play(Create(pyruvate_box), Write(pyruvate_txt), run_time=2.0)
        self.play(Write(pyruvate_label), run_time=1.0)
        self.wait(2.0)

        arrow_left = Arrow(pyruvate_box.get_left(), LEFT * 4 + DOWN * 1.5, color=RED, buff=0.1)
        no_o2_label = Text("No O2", font_size=18, color=RED)
        no_o2_label.next_to(arrow_left.get_center(), UP, buff=0.1)

        self.play(Create(arrow_left), Write(no_o2_label), run_time=1.5)
        self.wait(1.0)

        ethanol_box = Rectangle(width=1.8, height=0.7, color=PURPLE, fill_opacity=0.3).shift(LEFT * 4 + DOWN * 2)
        ethanol_txt = Text("Ethanol+CO2", font_size=20)
        ethanol_txt.move_to(ethanol_box)
        yeast_label = Text("(Yeast)", font_size=16)
        yeast_label.next_to(ethanol_box, DOWN, buff=0.15)

        self.play(Create(ethanol_box), Write(ethanol_txt), Write(yeast_label), run_time=2.0)
        self.wait(1.5)

        arrow_right = Arrow(pyruvate_box.get_right(), RIGHT * 4 + DOWN * 1.5, color=BLUE, buff=0.1)
        with_o2_label = Text("With O2", font_size=18, color=BLUE)
        with_o2_label.next_to(arrow_right.get_center(), UP, buff=0.1)

        self.play(Create(arrow_right), Write(with_o2_label), run_time=1.5)
        self.wait(1.0)

        co2_water_box = Rectangle(width=2, height=0.7, color=BLUE, fill_opacity=0.3).shift(RIGHT * 4 + DOWN * 2)
        co2_water_txt = Text("CO2 + H2O", font_size=20)
        co2_water_txt.move_to(co2_water_box)
        energy_label = Text("+ High Energy", font_size=16, color=GOLD)
        energy_label.next_to(co2_water_box, DOWN, buff=0.15)

        self.play(Create(co2_water_box), Write(co2_water_txt), Write(energy_label), run_time=2.0)
        self.wait(2.0)

        self.play(Circumscribe(co2_water_box, color=GOLD), run_time=1.5)
        self.wait(2.0)

        self.play(Indicate(title_s12, scale_factor=1.1), run_time=1.0)
        self.wait(2.4)

        self.play(FadeOut(*self.mobjects), run_time=0.5)
        self.wait(0.640)
        self.wait(0.1) # Terminal stabilizer