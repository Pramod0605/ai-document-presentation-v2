# Calculus: Integration and the Fundamental Theorem

## Topic 1: The Definite Integral

The definite integral represents the signed area under a curve between two points. For a function $f(x)$ continuous on the interval $[a, b]$, the definite integral is written as:

$$\int_{a}^{b} f(x)\,dx$$

This represents the limit of Riemann sums as the number of rectangles approaches infinity.

### Key Properties of Definite Integrals

- **Linearity**: $\int_{a}^{b} [f(x) + g(x)]\,dx = \int_{a}^{b} f(x)\,dx + \int_{a}^{b} g(x)\,dx$
- **Constant Multiple**: $\int_{a}^{b} c \cdot f(x)\,dx = c \cdot \int_{a}^{b} f(x)\,dx$
- **Additivity**: $\int_{a}^{c} f(x)\,dx = \int_{a}^{b} f(x)\,dx + \int_{b}^{c} f(x)\,dx$
- **Reversal**: $\int_{a}^{b} f(x)\,dx = -\int_{b}^{a} f(x)\,dx$

## Topic 2: The Fundamental Theorem of Calculus

The Fundamental Theorem of Calculus connects differentiation and integration. It has two parts:

### Part 1: Derivative of an Integral

If $F(x) = \int_{a}^{x} f(t)\,dt$, then:

$$\frac{d}{dx}\left[\int_{a}^{x} f(t)\,dt\right] = f(x)$$

This means the derivative of the integral function equals the original function.

### Part 2: Evaluating Definite Integrals

If $F(x)$ is an antiderivative of $f(x)$, then:

$$\int_{a}^{b} f(x)\,dx = F(b) - F(a)$$

This is often written using the notation $[F(x)]_{a}^{b} = F(b) - F(a)$.

## Topic 3: Calculating Antiderivatives

Common antiderivative formulas include:

| Function $f(x)$ | Antiderivative $F(x)$ |
|-----------------|----------------------|
| $x^n$ (n ≠ -1) | $\frac{x^{n+1}}{n+1}$ |
| $\frac{1}{x}$ | $\ln|x|$ |
| $e^x$ | $e^x$ |
| $\sin(x)$ | $-\cos(x)$ |
| $\cos(x)$ | $\sin(x)$ |

## Worked Example

Calculate $\int_{1}^{4} (3x^2 - 2x + 1)\,dx$

**Solution:**
1. Find the antiderivative: $F(x) = x^3 - x^2 + x$
2. Apply the Fundamental Theorem: $F(4) - F(1)$
3. Calculate: $(64 - 16 + 4) - (1 - 1 + 1) = 52 - 1 = 51$

## Quiz

1. What is $\int_{0}^{2} x^2\,dx$?
   - A) 4
   - B) 8/3
   - C) 2
   - D) 4/3

2. If $F(x) = \int_{0}^{x} \sin(t)\,dt$, what is $F'(\pi)$?
   - A) 0
   - B) 1
   - C) -1
   - D) $\pi$
