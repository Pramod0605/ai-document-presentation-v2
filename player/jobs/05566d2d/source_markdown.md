

# CHAPTER-1 (NUMBER SYSTEMS)

## REAL NUMBERS

## 1. INTRODUCTION TO REAL NUMBERS

### Real Numbers

### 1.1 Introduction

### 1.2 The Fundamental Theorem of Arithmetic

### 1.3 Revisiting

### 1.4 Summary

#### Definition

A real number is any number that can be represented as a point on the number line. The set of real numbers is denoted by  $\mathbb{R}$ .

#### Conceptual Expansion

Real numbers model continuous quantities — lengths, temperatures, speeds — where there are no “gaps.” This is unlike integers or rationals alone: between any two real numbers there are infinitely many others. The completeness (no gaps) of the real numbers is a foundational property used in calculus and analysis; at Class X level it simply means decimals can be extended indefinitely to approach limits.

#### Why the Number Line Matters

Every real number corresponds to a unique point on the number line and vice versa. This one-to-one correspondence helps in ordering, comparing magnitudes, and visualizing operations such as addition and subtraction.

#### Important Properties to Remember for Exams

- Every rational or irrational number is a real number.
- Real numbers can be positive, negative, or zero.
- Between any two distinct real numbers there are infinitely many rational and infinitely many irrational numbers.

#### Short Exam-Answer Format

“Real numbers are all numbers that can be located on the number line; they include rational and irrational numbers. They form a continuous set — between any two real numbers there exist infinitely many other real numbers.”

## 2. CLASSIFICATION OF REAL NUMBERS

(Write hierarchically in exams: name → definition → example → key property)

### 2.1 Natural Numbers (N)

- **Definition:** Positive integers used for counting: 1, 2, 3, ...
- **Example:** 7 (number of days in a week).
- **Exam Tip:** Do not include 0.

### 2.2 Whole Numbers (W)

- **Definition:** Natural numbers plus 0: 0, 1, 2, ...
- **Example:** 0 (no apples left).
- **Property:** All whole numbers are integers and hence real.

### 2.3 Integers (Z)

- **Definition:** ..., -3, -2, -1, 0, 1, 2, 3, ...
- **Use:** Represent losses or negative directions.
- **Property:** Closed under addition and subtraction.

### 2.4 Rational Numbers (Q)

- **Definition:** Numbers expressible as  $p/q$ , where  $p$  and  $q$  are integers and  $q \neq 0$ .
- **Decimal Nature:** Terminating or non-terminating repeating.
- **Examples:**  $-2/5$ , 0.2,  $7/3$ .
- **Important Property:** Rational numbers have eventually repeating decimal expansions.

### 2.5 Irrational Numbers

- **Definition:** Real numbers that are not rational; cannot be written as  $p/q$ .
- **Decimal Nature:** Non-terminating, non-repeating decimals.

- **Examples:**  $\sqrt{2}$ ,  $\sqrt{3}$ ,  $\pi$ .
- **Exam Note:** Usually proved using contradiction and prime factorization/parity arguments.

### 2.6 Real Numbers (R)

- **Definition:**  $R = Q \cup \{\text{irrational numbers}\}$ .
- **Exam Statement:** "Real numbers include all rational and irrational numbers; they can all be represented on a number line."

## 3. FUNDAMENTAL THEOREM OF ARITHMETIC (FTA)

### Formal Statement (Exam-Perfect)

Every integer greater than 1 is either a prime or can be written as a product of primes; this factorization is unique up to the order of the prime factors.

### Why It Matters

- Primes are the building blocks of natural numbers.
- Uniqueness allows consistent definitions of HCF and LCM.

#### Proof Idea

#### Existence (Strong Induction):

- Base case: 2 is prime.
- If n is composite,  $n = ab$ , where  $1 < a, b < n$ . By induction, a and b have prime factorizations.

#### Uniqueness (Contradiction):

- Assume two different prime factorizations.
- Cancel common primes using divisibility.
- Reach a contradiction.

### Useful Exam Sentence

"FTA guarantees unique prime factorization (up to order), which is essential for computing HCF and LCM."

#### Example: Prime Factorisation

**Question:** Find the prime factorisation of 32760.

#### Solution (Step-by-Step):

1.  $32760 \div 2 = 16380$

2.  $16380 \div 2 = 8190$

3.  $8190 \div 2 = 4095$

4.  $4095 \div 3 = 1365$

5.  $1365 \div 3 = 455$

6.  $455 \div 5 = 91$

7.  $91 = 7 \times 13$

#### **Final Answer:**

$$32760 = 2^3 \times 3^2 \times 5 \times 7 \times 13$$

## 4. APPLICATIONS OF FTA

### Application A — HCF Using Prime Factorisation

##### **Method:**

1. Prime factorise all numbers.
2. Take common primes with lowest powers.
3. Multiply them.

**Example:** Find HCF of 180 and 308.

$$180 = 2^2 \times 3^2 \times 5$$

$$308 = 2^2 \times 7 \times 11$$

$$\text{Common prime} = 2^2$$

$$\text{HCF} = 4$$

##### **Key Fact:**

$$\text{HCF} \times \text{LCM} = \text{Product of the numbers.}$$

### Application B — LCM Using Prime Factorisation

##### Method:

1. Prime factorise each number.
2. Take all primes with highest powers.
3. Multiply them.

**Example:** LCM of 180 and 308.

$$\text{LCM} = 2^2 \times 3^2 \times 5 \times 7 \times 11 = 27720$$

### Application C — Proving Irrationality ( $\sqrt{2}$ )

1. Assume  $\sqrt{2} = p/q$  in lowest terms.
2. $p^2 = 2q^2$ .
3. $p$  is even  $\Rightarrow p = 2k$ .
4. $q^2 = 2k^2 \Rightarrow q$  even.
5. Contradiction.
6. Therefore  $\sqrt{2}$  is irrational.

**General Result:**  $\sqrt{p}$  is irrational for any prime  $p$ .

### Application D — Real-Life Problems

- Smallest divisible number  $\to$  LCM
- Largest equal division  $\to$  HCF

## 5. SOLUTIONS TO EXERCISE 1.1 (IMPORTANT EXAM QUESTIONS)

#### Problem 4

Given: HCF(306, 657) = 9

$$\text{LCM} = (306 \times 657) \div 9 = 22338$$

#### Problem 5

Can  $6^n$  end with digit 0?

$$6 = 2 \times 3 \Rightarrow 6^n = 2^n \times 3^n \text{ (no factor 5)}$$

**Conclusion:**  $6^n$  cannot end with 0.

#### **Problem 7 (Circular Track)**

$$\text{LCM}(18, 12) = 36$$

**They meet after 36 minutes.**

## 6. IMPORTANT QUESTIONS FOR EXAMS

### Very Short Answer

1. Define real numbers.

Answer:

Real numbers are all numbers that can be represented on the number line. They include both rational and irrational numbers and are denoted by  $\mathbb{R}$ .

2. State the Fundamental Theorem of Arithmetic.

Answer:

Every integer greater than 1 is either a prime number or can be expressed as a product of prime numbers, and this factorization is unique except for the order of the prime factors.

### Short Answer

3. Find HCF using prime factorization.

Answer:

Steps:

1. Prime factorise the given numbers.
2. Identify the common prime factors.
3. Take the lowest powers of the common primes.
4. Multiply them to obtain the HCF.

Example:

Find HCF of 24 and 60.

$$24 = 2^3 \times 3$$

$$60 = 2^2 \times 3 \times 5$$

Common primes =  $2^2$  and  $3^1$

$$\text{HCF} = 2^2 \times 3 = 12$$

4. Express a number as a product of primes.

Answer:

Example: Express 252 as a product of prime factors.

$$252 \div 2 = 126$$

$$126 \div 2 = 63$$

$$63 \div 3 = 21$$

$$21 \div 3 = 7$$

So,

$$252 = 2^2 \times 3^2 \times 7$$

Thus, 252 expressed as a product of primes is  $2^2 \times 3^2 \times 7$ .

### Long Answer

5. Prove that  $\sqrt{2} / \sqrt{3} / \sqrt{5}$  is irrational.

*(Method shown for  $\sqrt{2}$ ; same logic applies to  $\sqrt{3}$  and  $\sqrt{5}$ )*

Proof:

Assume  $\sqrt{2}$  is rational.

Then  $\sqrt{2} = p/q$ , where p and q are coprime integers and  $q \neq 0$ .

Squaring both sides,

$$2 = p^2/q^2$$

$$\Rightarrow p^2 = 2q^2$$

So,  $p^2$  is even  $\Rightarrow p$  is even.

Let  $p = 2k$ .

Substitute in  $p^2 = 2q^2$ :

$$(2k)^2 = 2q^2$$

$$\Rightarrow 4k^2 = 2q^2$$

$$\Rightarrow q^2 = 2k^2$$

Thus,  $q$  is also even.

This contradicts the assumption that  $p$  and  $q$  are coprime.

Therefore,  $\sqrt{2}$  is irrational.

Similarly,  $\sqrt{3}$  and  $\sqrt{5}$  can also be proved irrational.

6. Find HCF and LCM using Fundamental Theorem of Arithmetic.

Example: Find HCF and LCM of 72 and 120.

Prime Factorization:

$$72 = 2^3 \times 3^2$$

$$120 = 2^3 \times 3 \times 5$$

HCF:

Take common primes with lowest powers:

$$\text{HCF} = 2^3 \times 3 = 24$$

LCM:

Take all primes with highest powers:

$$\text{LCM} = 2^3 \times 3^2 \times 5 = 360$$

Final Answer:

$$\text{HCF} = 24$$

$$\text{LCM} = 360$$

## 7. EXTENDED SUMMARY

Real numbers include rational and irrational numbers and can be represented on a number line. Rational numbers have terminating or repeating decimals, while irrational numbers have non-terminating, non-repeating decimals. The Fundamental Theorem of Arithmetic states that every composite number has a unique prime factorization. Using FTA, we can find HCF, LCM, and prove irrationality of certain numbers.

## 8. EXAM FOCUS

### High-Yield Topics:

- Proof of irrationality
- HCF and LCM numericals
- Statement and use of FTA
- Classification of numbers

### Common Errors:

- Skipping lowest terms
- Incorrect prime powers
- Confusing repeating and non-repeating decimals

## 9. SAMPLE ANSWER TEMPLATES

### Proving $\sqrt{2}$ Is Irrational

Assume  $\sqrt{2} = p/q$  in lowest terms.

$$p^2 = 2q^2$$

$$p \text{ even} \Rightarrow q \text{ even}$$

Contradiction  $\Rightarrow \sqrt{2}$  is irrational.

### HCF and LCM of 72 and 108

$$72 = 2^3 \times 3^2$$

$$108 = 2^2 \times 3^3$$

$$\text{HCF} = 36$$

$$\text{LCM} = 216$$

## 10. PRACTICE QUESTIONS

1. Express 2310 as product of primes.
2. Find HCF and LCM of 84, 90, 126.
3. Prove  $\sqrt{3}$  is irrational.

# UNIT I – NUMBER SYSTEMS

## REAL NUMBERS

### Question Bank with Answers & Step-by-Step Solutions (Class X – CBSE)

#### SECTION A – MCQs (1 × 10)

Q1. Which of the following numbers is irrational?

(a) 0.375  
(b)  $\frac{5}{11}$   
(c)  $\sqrt{7}$   
(d) -3

**Answer:** (c)

Q2. The decimal expansion of  $\frac{13}{40}$  is:

(a) non-terminating non-repeating  
(b) non-terminating repeating  
(c) terminating  
(d) none

**Answer:** (c)

Q3. Which has a terminating decimal expansion?

(a)  $\frac{7}{12}$   
(b)  $\frac{13}{125}$   
(c)  $\frac{11}{45}$   
(d)  $\frac{29}{30}$

**Answer:** (b)

Q4. According to the Fundamental Theorem of Arithmetic, every composite number can be written as a product of prime numbers.

Q5. HCF = 12, LCM = 180, one number = 36.

**Answer:** 60

#### SECTION B – Very Short Answer (2 Marks)

Q6. State the Fundamental Theorem of Arithmetic.

Answer: Every integer greater than 1 is either a prime or can be expressed as a product of prime numbers; this factorization is unique except for the order of the prime factors.

Q7. Write one rational and one irrational number.

Answer: Rational:  $3/5$

Irrational:  $\sqrt{2}$

Q8. Is  $\sqrt{36}$  rational? Justify.

Answer: Yes.  $\sqrt{36} = 6$ , and  $6 = 6/1$  is a rational number.

Q9. Write the prime factorization of 90.

Answer:  $90 = 2 \times 45 = 2 \times 3 \times 15 = 2 \times 3 \times 3 \times 5 = 2 \times 3^2 \times 5$

#### SECTION C – Short Answer (3 Marks)

Q10. Find the HCF and LCM of 24 and 60.

Step 1 — Prime factorization:

$$24 = 2^3 \times 3$$

$$60 = 2^2 \times 3 \times 5$$

$$\text{HCF: common primes with lowest powers} = 2^2 \times 3 = 12$$

$$\text{LCM: all primes with highest powers} = 2^3 \times 3 \times 5 = 120$$

Answer: HCF = 12, LCM = 120

Q11. Determine whether  $7/125$  has a terminating decimal expansion.

$$125 = 5^3 \text{ (only prime factor 5).}$$

A fraction in lowest terms has a terminating decimal iff denominator has only 2 and/or 5 as prime factors.

Therefore  $7/125$  has a terminating decimal expansion.

$$7/125 = 0.056$$

Answer: Yes, terminating (0.056).

Q12. Express 252 as a product of prime factors.

$$252 \div 2 = 126$$

$$126 \div 2 = 63$$

$$63 \div 3 = 21$$

$$21 \div 3 = 7$$

$$252 = 2^2 \times 3^2 \times 7$$

#### SECTION D – Long Answer (5 Marks)

##### Q13. Prove that $\sqrt{2}$ is irrational.

Proof: Assume  $\sqrt{2}$  is rational. Then  $\sqrt{2} = p/q$  in lowest terms ( $p$ ,  $q$  integers,  $q \neq 0$ ,  $\text{gcd}(p,q)=1$ ).

$$\text{Square both sides: } 2 = p^2/q^2 \Rightarrow p^2 = 2q^2.$$

So  $p^2$  is even  $\Rightarrow p$  is even. Let  $p = 2k$ . Then  $p^2 = 4k^2$ , so  $4k^2 = 2q^2 \Rightarrow q^2 = 2k^2 \Rightarrow q^2$  is even  $\Rightarrow q$  is even.

Thus  $p$  and  $q$  are both even, contradicting  $\text{gcd}(p,q)=1$ .

Therefore  $\sqrt{2}$  is irrational.

##### Q14. Find HCF and LCM of 72 and 120.

Prime factorization:

$$72 = 2^3 \times 3^2$$

$$120 = 2^3 \times 3 \times 5$$

$$\text{HCF} = \text{common primes with lowest powers} = 2^3 \times 3 = 24$$

$$\text{LCM} = \text{all primes with highest powers} = 2^3 \times 3^2 \times 5 = 360$$

Answer: HCF = 24, LCM = 360

##### Q15. Determine whether $15/160$ has a terminating decimal expansion.

Simplify fraction:  $15/160 = 3/32$ .

$32 = 2^5$  (only prime factor 2). Therefore decimal expansion is terminating.

$$3/32 = 0.09375$$

Answer: Yes, terminating (0.09375).

#### SECTION E – Case Study Based Question (5 Marks)

##### Q16. Distribution of 540 notebooks and 756 pens equally.

Find maximum number of students = HCF(540, 756).

Prime factorization:

$$540 = 2^2 \times 3^3 \times 5$$

$$756 = 2^2 \times 3^3 \times 7$$

$$\text{HCF} = 2^2 \times 3^3 = 108$$

$$\text{Notebooks per student} = 540 \div 108 = 5$$

$$\text{Pens per student} = 756 \div 108 = 7$$

Answer: 108 students; each gets 5 notebooks and 7 pens.

#### SECTION F – HOTS Questions

**Q17. Can the product of two irrational numbers be rational?**

Answer: Yes. Example:  $\sqrt{2} \times \sqrt{2} = 2$  (both factors irrational, product rational).

**Q18. Prove that  $3 + \sqrt{5}$  is irrational.**

Proof: Suppose  $3 + \sqrt{5}$  is rational. Then  $\sqrt{5} = (3 + \sqrt{5}) - 3$  would be difference of two rationals, hence rational. This contradicts the known irrationality of  $\sqrt{5}$ . Therefore  $3 + \sqrt{5}$  is irrational.

#### SECTION G – Extra Numerical Practice (Solved)

**Q19. LCM of 48, 60, 72 = 720**

Work:

$$48 = 2^4 \times 3$$

$$60 = 2^2 \times 3 \times 5$$

$$72 = 2^3 \times 3^2$$

$$\text{LCM} = 2^4 \times 3^2 \times 5 = 16 \times 9 \times 5 = 720$$

**Q20.  $19/125 = 0.152$  (terminating)**

Reason:  $125 = 5^3$ , so denominator has only prime factor 5  $\to$  terminating decimal.

### FINAL EXAM TIP

- Always show prime factorization clearly
- Write theorem statements
- Proofs must be step-wise
- High-scoring chapter (5–6 marks)