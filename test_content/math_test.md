# Advanced Mathematics: Quadratic Equations and Geometry

## Quadratic Formula

The quadratic formula is one of the most important formulas in algebra. For any quadratic equation in the form $ax^2 + bx + c = 0$, the solutions are given by:

$$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$

Let's understand each part:
- The term $b^2 - 4ac$ is called the discriminant
- When the discriminant is positive, we get two real solutions
- When the discriminant is zero, we get one repeated solution
- When the discriminant is negative, we get two complex solutions

### Example Problem

Solve $2x^2 + 5x - 3 = 0$

Here we have:
- $a = 2$
- $b = 5$  
- $c = -3$

Substituting into the formula:
$$x = \frac{-5 \pm \sqrt{25 + 24}}{4} = \frac{-5 \pm 7}{4}$$

Therefore $x = \frac{1}{2}$ or $x = -3$

## Pythagorean Theorem

In a right triangle, the relationship between the sides is:

$$a^2 + b^2 = c^2$$

Where $c$ is the hypotenuse (the longest side, opposite the right angle) and $a$ and $b$ are the other two sides.

### Geometric Proof

Consider a square with side length $(a + b)$. We can arrange four copies of our right triangle inside it, leaving a smaller square of side $c$ in the middle.

The area of the large square is $(a + b)^2 = a^2 + 2ab + b^2$

The area can also be calculated as: $4 \times \frac{1}{2}ab + c^2 = 2ab + c^2$

Setting these equal: $a^2 + 2ab + b^2 = 2ab + c^2$

Simplifying: $a^2 + b^2 = c^2$

## Derivatives and Calculus

The derivative of a function measures its instantaneous rate of change. For $f(x) = x^n$:

$$\frac{d}{dx}(x^n) = nx^{n-1}$$

This is called the power rule.

### Chain Rule

For composite functions $f(g(x))$:

$$\frac{d}{dx}[f(g(x))] = f'(g(x)) \cdot g'(x)$$

### Example: Area of a Circle

The area of a circle is $A = \pi r^2$

Taking the derivative with respect to $r$:
$$\frac{dA}{dr} = 2\pi r$$

This gives us the circumference! This shows how the area changes as the radius increases.

## Trigonometry

The fundamental trigonometric identity:

$$\sin^2(\theta) + \cos^2(\theta) = 1$$

On the unit circle, for any angle $\theta$:
- $\cos(\theta)$ gives the x-coordinate
- $\sin(\theta)$ gives the y-coordinate

### Sum Formulas

$$\sin(A + B) = \sin(A)\cos(B) + \cos(A)\sin(B)$$

$$\cos(A + B) = \cos(A)\cos(B) - \sin(A)\sin(B)$$

## Geometric Shapes

### Area Formulas

| Shape | Formula |
|-------|---------|
| Rectangle | $A = l \times w$ |
| Triangle | $A = \frac{1}{2}bh$ |
| Circle | $A = \pi r^2$ |
| Trapezoid | $A = \frac{1}{2}(a + b)h$ |

### Volume Formulas

For a sphere: $V = \frac{4}{3}\pi r^3$

For a cylinder: $V = \pi r^2 h$

For a cone: $V = \frac{1}{3}\pi r^2 h$
