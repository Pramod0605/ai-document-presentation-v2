# Introduction to Derivatives and Differentiation

## Introduction

Calculus is one of the most powerful tools in mathematics. Today, we will explore the concept of derivatives, which forms the foundation of differential calculus. Understanding derivatives will enable you to analyze rates of change, optimize functions, and model real-world phenomena.

## Learning Objectives

By the end of this lesson, you will be able to:
- Define the derivative of a function using the limit definition
- Apply the power rule to find derivatives of polynomial functions
- Interpret the derivative as the slope of a tangent line
- Calculate derivatives of common functions
- Apply differentiation to solve rate of change problems

## Core Concepts

### Concept 1: The Definition of a Derivative

The derivative of a function f(x) at a point x is defined as:

$$f'(x) = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}$$

This limit represents the instantaneous rate of change of the function at that point. Geometrically, the derivative gives us the slope of the tangent line to the curve at any point.

Key terms:
- Derivative
- Limit definition
- Instantaneous rate of change
- Tangent line

### Concept 2: The Power Rule

The power rule is the most fundamental differentiation rule. For any function of the form f(x) = x^n where n is a real number:

$$\frac{d}{dx}[x^n] = nx^{n-1}$$

To apply the power rule:
1. Multiply by the current exponent
2. Reduce the exponent by 1

Examples:
- If f(x) = x^3, then f'(x) = 3x^2
- If f(x) = x^5, then f'(x) = 5x^4
- If f(x) = x^{-2}, then f'(x) = -2x^{-3}

### Concept 3: Sum and Difference Rules

When differentiating sums or differences of functions:

$$\frac{d}{dx}[f(x) + g(x)] = f'(x) + g'(x)$$

$$\frac{d}{dx}[f(x) - g(x)] = f'(x) - g'(x)$$

This means we can differentiate term by term.

### Concept 4: The Constant Multiple Rule

For any constant c multiplied by a function:

$$\frac{d}{dx}[c \cdot f(x)] = c \cdot f'(x)$$

Constants can be factored out before differentiating.

### Concept 5: Geometric Interpretation

The derivative at a point x = a gives:
- The slope of the tangent line at (a, f(a))
- The instantaneous rate of change at x = a
- The velocity if f(t) represents position

A positive derivative means the function is increasing.
A negative derivative means the function is decreasing.
A zero derivative means the function has a horizontal tangent (possible maximum or minimum).

## Worked Example

**Problem**: Find the derivative of f(x) = 3x^4 - 2x^3 + 5x - 7 and evaluate it at x = 2.

**Solution**:

Step 1: Apply the power rule and constant multiple rule to each term.
- Derivative of 3x^4: 3 · 4x^3 = 12x^3
- Derivative of -2x^3: -2 · 3x^2 = -6x^2
- Derivative of 5x: 5 · 1 = 5
- Derivative of -7: 0 (constant)

Step 2: Combine the results.
$$f'(x) = 12x^3 - 6x^2 + 5$$

Step 3: Evaluate at x = 2.
$$f'(2) = 12(2)^3 - 6(2)^2 + 5$$
$$f'(2) = 12(8) - 6(4) + 5$$
$$f'(2) = 96 - 24 + 5$$
$$f'(2) = 77$$

**Answer**: The derivative is f'(x) = 12x^3 - 6x^2 + 5, and f'(2) = 77.

This means the slope of the tangent line to f(x) at x = 2 is 77.

## Practice Quiz

1. What is the derivative of f(x) = x^7?
   a) x^6
   b) 7x^6
   c) 7x^7
   d) 6x^7

2. What does a derivative of zero indicate?
   a) The function is undefined
   b) The function has a horizontal tangent
   c) The function is always increasing
   d) The function equals zero

3. Using the power rule, find the derivative of g(x) = 4x^3.
   a) 12x^2
   b) 4x^2
   c) 3x^2
   d) 12x^3

4. What is the geometric meaning of the derivative?
   a) The area under the curve
   b) The slope of the tangent line
   c) The y-intercept
   d) The maximum value

5. If f(x) = x^2 + 3x + 2, what is f'(x)?
   a) 2x + 3
   b) x^2 + 3
   c) 2x + 3x
   d) x + 3

## Summary

In this lesson, we covered the fundamental concepts of derivatives:

1. **Definition**: The derivative is the limit of the difference quotient, representing instantaneous rate of change.

2. **Power Rule**: For f(x) = x^n, the derivative is f'(x) = nx^{n-1}.

3. **Sum/Difference Rule**: Derivatives of sums and differences can be computed term by term.

4. **Constant Multiple Rule**: Constants factor out of the derivative.

5. **Geometric Interpretation**: The derivative gives the slope of the tangent line and indicates whether a function is increasing or decreasing.

Mastering these concepts provides the foundation for all of differential calculus.
