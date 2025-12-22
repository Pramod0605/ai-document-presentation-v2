# Gap Analysis Report - Job 0a6fb562

## Executive Summary
**Critical Issue**: Smart Chunker identified 5 topics, but Content Director only created 2 content sections. 3 topics from source markdown are MISSING from final presentation.

---

## Source Markdown Analysis (5 Topics)

| # | Subject | Topic Title | Has LaTeX |
|---|---------|-------------|-----------|
| 1 | Biology | The Endosymbiotic Theory | No |
| 2 | Mathematics | The Fundamental Theorem of Calculus | Yes: `\int_{a}^{b} f(x)\,dx = F(b) - F(a)` |
| 3 | Geometry | Area of a Sector and Volume | Yes: `A = \frac{1}{2} r^2 \theta`, `V = \pi r^2 h` |
| 4 | Physics | Wave Period and Frequency | Yes: `v = f \lambda`, `T = \frac{1}{f}` |
| 5 | Chemistry | The Equilibrium Constant (Kc) | Yes: `K_c = \frac{[C]^c [D]^d}{[A]^a [B]^b}` |

---

## Presentation.json Sections (7 Total)

| Section ID | Type | Title | Source Topic |
|------------|------|-------|--------------|
| section_1 | intro | Welcome to Your Science Lesson! | Generated (not from source) |
| section_2 | summary | Lesson Summary | Generated (not from source) |
| section_3 | content | The Endosymbiotic Theory | ✅ Biology (Topic 1) |
| section_4 | example | Example: Calculating Wave Speed | ✅ Physics (Topic 4) - BUT AS EXAMPLE NOT CONTENT |
| section_5 | quiz | Knowledge Check | ❌ FABRICATED - No quiz in source |
| section_6 | memory | Remember This! | Generated (not from source) |
| section_7 | recap | Untitled | Generated (not from source) |

---

## CRITICAL GAPS

### Gap 1: 3 Topics Missing (60% Content Loss)
**Missing from presentation:**
- ❌ Mathematics: Fundamental Theorem of Calculus
- ❌ Geometry: Area of a Sector and Volume  
- ❌ Chemistry: Equilibrium Constant Kc

**Root Cause**: Smart Chunker identified 5 topics (confirmed in logs), but Content Director only created 2 content sections. The Content Director is NOT creating one section per topic.

### Gap 2: Physics Topic Misclassified as "Example"
- Source: Topic about Wave Period and Frequency
- Presentation: Shown as "Example: Calculating Wave Speed"
- Issue: Should be a "content" section, not "example". The source has formulas but no worked example.

### Gap 3: Quiz Fabricated When None Exists
- Source markdown has NO quiz or exercise content
- Presentation includes a "Knowledge Check" quiz section
- Issue: ISS-097 - Quiz should be conditional, not always generated

### Gap 4: LaTeX Not Rendered in Display
- Source has 6+ LaTeX formulas
- Only 1 formula appears in presentation (Wave Speed)
- Missing: Integral formula, Sector Area, Cylinder Volume, Period formula, Equilibrium Constant

---

## Display Issues (From Screenshot)

### Issue 1: Avatar Layout
- Avatar starts large/center, then slides to side with text behind
- Expected: Smooth transition, text should not overlap avatar
- Root Cause: Layout configuration in intro section says center/50%, but summary says right/40%

### Issue 2: Summary Content Incomplete
- Screenshot shows: Endosymbiotic Theory (3 bullets) + Wave Mechanics
- Missing: Mathematics, Geometry, Chemistry topics
- Root Cause: Summary only mentions 2 of 5 source topics because Content Director only created 2 sections

### Issue 3: Bullet Points Are Sentences
- Summary bullet "Mitochondria & Chloroplasts were once independent prokaryotes." is a sentence
- Expected: Short bullet keywords, not full sentences
- This follows the source text pattern

---

## Pipeline Data Flow Analysis

```
Source .md (5 topics)
       ↓
Smart Chunker → Identified 5 topics ✓
       ↓
Content Director → Created only 2 content sections ✗ (BOTTLENECK)
       ↓
Presentation.json (missing 3 topics)
       ↓
Player Display (incomplete content)
```

---

## Recommended Fixes

### Priority 1: Content Director Topic Coverage
- Content Director prompt must create ONE content section per topic from Smart Chunker
- Currently appears to be summarizing/combining topics instead of teaching each
- Add validation: Number of content sections >= Number of chunker topics

### Priority 2: LaTeX Passthrough
- Source LaTeX formulas must be preserved and passed to presentation
- Content Director should extract and include formulas in visual_content.formula
- Player must render LaTeX (check if MathJax/KaTeX is configured)

### Priority 3: Conditional Quiz (ISS-097)
- Already logged - implement has_quiz flag from Smart Chunker

### Priority 4: Avatar Layout Transitions
- Review layout configuration for smooth transitions between sections
- Text should not overlap avatar

---

## Files to Review
- `core/prompts/content_director_system_v1.4.txt` - Topic-to-section mapping
- `core/prompts/chunker_prompt.txt` - Topic extraction
- `player/player.js` - Avatar/text layout handling

---

Generated: 2025-12-22
Job ID: 0a6fb562
