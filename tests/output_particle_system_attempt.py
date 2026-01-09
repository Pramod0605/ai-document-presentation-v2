from manim import *

class MainScene(Scene):
    def construct(self):
        # Segment 1 (5.0s): Gas molecules moving
        # Create container
        box = Rectangle(height=4, width=5)
        
        # Create just 3 representative molecules (not 50)
        mol1 = Circle(radius=0.2).set_fill(BLUE, opacity=0.8)
        mol2 = Circle(radius=0.2).set_fill(BLUE, opacity=0.8)
        mol3 = Circle(radius=0.2).set_fill(BLUE, opacity=0.8)
        
        # Set initial positions
        mol1.move_to([-1, 0, 0])
        mol2.move_to([1, 1, 0])
        mol3.move_to([0, -1, 0])

        # Show container and molecules
        self.play(
            Create(box),
            FadeIn(mol1, mol2, mol3),
            run_time=1.0
        )

        # Animate random motion
        self.play(
            mol1.animate.move_to([1, -1, 0]),
            mol2.animate.move_to([-1, -0.5, 0]),
            mol3.animate.move_to([0.5, 1, 0]),
            run_time=2.0
        )

        # Continue motion in different direction
        self.play(
            mol1.animate.move_to([-0.5, 0.5, 0]),
            mol2.animate.move_to([1, 0, 0]),
            mol3.animate.move_to([-1, -1, 0]),
            run_time=1.5
        )

        self.wait(0.5)