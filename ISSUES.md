# Known Issues & Future Improvements

## ISS-212: Token Optimization Between Agents
**Status:** Logged for future work
**Priority:** Medium
**Description:** Currently passing full JSON payloads between agents (Chunker → SectionPlanner → ContentCreator). Can reduce token usage by ~50% by:
1. Using compact topic summaries instead of full JSON for SectionPlanner input
2. Passing only essential fields (topic_id, title, complexity_tag) instead of full objects
3. Consider structured output schemas to reduce verbosity

**Current Cost:** ~8-12K tokens overhead per job for JSON passing
**Potential Savings:** ~4-6K tokens per job

---

## ISS-213: Smart Chunker Content Density Analysis
**Status:** In Progress
**Priority:** High
**Description:** Chunker needs to analyze content density and recommend how many content sections are needed. Currently just splits by headers without considering:
1. Number of concepts/bullet points per section
2. Complexity of content (formulas, tables, images)
3. Recommended section count based on density

**Root Cause:** Without density analysis, SectionPlanner creates arbitrary section counts, causing ContentCreator to exceed segment limits on dense content.

**Solution:** Add content_density_analysis output with recommended_content_sections count.

---
