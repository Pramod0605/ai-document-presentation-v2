# Dry Run Report - ISS-056 Visual Content Test
**Job ID:** c7396443  
**Date:** 2025-12-21  
**Spec Version:** v1.3  
**Subject:** Biology  
**Grade:** Class 10  

---

## Summary

| Metric | Result |
|--------|--------|
| **Director Pass** | ✅ PASSED (3 validation tiers) |
| **Section Count** | 8 |
| **Mandatory Sections** | ✅ All present (intro, summary, memory, recap) |
| **visual_content Populated** | 7/8 sections (87.5%) |
| **Total Cost** | $0.63 |
| **Total Duration** | 458s |

---

## ISS-056 Two-Channel Separation Test

### Test Objective
Verify that the Director LLM correctly populates `visual_content` for screen display, keeping `narration.text` as audio-only.

### Results

| Section | Type | Has visual_content | Status |
|---------|------|-------------------|--------|
| 1 | intro | ✅ Yes | **PASS** |
| 2 | summary | ✅ Yes | **PASS** |
| 3 | content | ✅ Yes | **PASS** |
| 4 | content | ✅ Yes | **PASS** |
| 5 | content | ✅ Yes | **PASS** |
| 6 | content | ✅ Yes | **PASS** |
| 7 | memory | ✅ Yes | **PASS** |
| 8 | recap | ❌ No | **EXPECTED** (recap is video-only) |

### Sample Output - Content Section (Section 3)

**Narration Text (Audio Only):**
> "The brain is incredibly soft, with a consistency similar to jelly. To protect this delicate structure, our body has a multi-layered defense system..."

**Visual Content (Screen Display):**
```json
{
  "bullet_points": [
    { "level": 1, "text": "The brain is a delicate organ" },
    { "level": 1, "text": "Protection of the Brain" },
    { "level": 2, "text": "Bony box or Cranium (Skull)" }
  ]
}
```

**Display Directives:**
```json
{
  "text_layer": "show",
  "visual_layer": "hide",
  "avatar_layer": "show"
}
```

✅ **Two-channel separation confirmed**: Narration text is distinct from visual_content bullets

---

## Validation Results

### Tier-1 Structural
- Initial attempt: FAILED (5 errors - display directive violations, missing video_prompts)
- Retry 1: PASSED

### Tier-2 Semantic
- Initial attempt: FAILED (2 errors - word count below minimum)
- Retry 1: PASSED

### Tier-3 Quality Lint
- No warnings

---

## Pipeline Analytics

| Phase | Duration | Cost | Tokens |
|-------|----------|------|--------|
| Chunker | 2.02s | $0.001 | 913 |
| Director | 102.92s | $0.129 | 16,965 |
| Director Retry 1 | 116.41s | $0.176 | 27,598 |
| Director Retry 2 | 113.07s | $0.172 | 28,099 |
| Remotion Renderer (3 sections) | ~38s | $0.048 | 6,641 |
| Video Renderer (5 sections) | ~85s | $0.100 | 17,709 |

---

## Known Issues

1. **Remotion Section 1 Parse Error**: The LLM returned garbled text instead of JSON for the intro section remotion render. This is a model response issue, not a schema issue.

2. **Visual Beat Compilation Failures**: 4 content sections failed to compile visual beats for WAN rendering due to "no content" errors. This is related to the video_prompts structure, not visual_content.

---

## Conclusion

**ISS-056 is RESOLVED.** The Director correctly:
1. Separates narration text (audio) from visual_content (display)
2. Populates bullet_points with level hierarchy (1 = main, 2 = sub)
3. Sets display_directives.text_layer="show" when visual_content should appear
4. Extracts structured content from source document for display
