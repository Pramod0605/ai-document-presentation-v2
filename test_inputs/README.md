# V1.4 Test Input Files

Test cases for V1.4 Split Director Architecture covering all renderer scenarios.

## Test Files

| File | Subject | Expected Renderers | Key Tests |
|------|---------|-------------------|-----------|
| `test_math_calculus.md` | Math | Manim (content), Remotion (intro/summary) | manim_scene_spec generation, formula rendering |
| `test_physics_motion.md` | Physics | Manim (content), Remotion (intro/summary) | kinematic equations, Newton's laws visualization |
| `test_biology_cells.md` | Biology | Video/WAN (content), Remotion (intro/summary) | Cell processes, organelle animations |
| `test_chemistry_reactions.md` | Chemistry | Video/WAN (content), Manim (equations) | Reaction animations, equation balancing |

## Expected Validation

### Math/Physics (Manim Required)
- Each manim section MUST have `manim_scene_spec` with:
  - `objects` array (equations, graphs, shapes)
  - `animation_sequence` array (actions with durations)
- Each manim/video section MUST have `visual_beats` array

### Biology (Video/WAN Required)
- Sections use `renderer: "video"`
- Each video section MUST have `visual_beats` with descriptive prompts
- Video prompts should be 100+ words (expanded by renderer)

### Chemistry (Mixed)
- Reaction processes: `renderer: "video"`
- Equation balancing: `renderer: "manim"`

## Running Tests

```bash
# Test Math (Manim)
curl -X POST http://localhost:5000/api/v14/generate \
  -H "Content-Type: application/json" \
  -d '{"markdown": "<contents of test_math_calculus.md>", "subject": "Mathematics", "grade": "Grade 12", "skip_wan": true}'

# Test Biology (Video/WAN)
curl -X POST http://localhost:5000/api/v14/generate \
  -H "Content-Type: application/json" \
  -d '{"markdown": "<contents of test_biology_cells.md>", "subject": "Biology", "grade": "Grade 10", "skip_wan": false}'
```

## Validation Checklist

- [ ] ISS-106: Renderers execute (videos folder populated)
- [ ] ISS-107: All segments have duration_estimate > 0
- [ ] ISS-109: Manim sections have manim_scene_spec
- [ ] ISS-110: Content Director analytics show cost > 0
- [ ] Memory section has 5 flashcards
- [ ] Recap section has 5 scenes with video_prompts
