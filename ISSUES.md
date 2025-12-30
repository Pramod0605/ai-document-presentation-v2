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
**Status:** ✅ DONE (2025-12-30)
**Priority:** High
**Description:** Chunker needs to analyze content density and recommend how many content sections are needed.

**Solution Implemented:**
1. Added `content_density_analysis` output with `recommended_content_sections` count
2. Added `topic_grouping_hints` for section assignment
3. SectionPlanner now consumes density recommendations
4. Pipeline uses chunker's source_blocks directly instead of re-parsing markdown

---

## ISS-214: Remove max_tokens Limits from All LLM Agents
**Status:** Open
**Priority:** High
**Description:** Multiple agents have hardcoded max_tokens limits (8K-18K) that cause JSON truncation errors when generating long outputs.

**Symptoms:**
- `[RendererSpec] Invalid JSON response: Unterminated string at char 25118`
- Agents fail after 3 retries due to truncated JSON

**Affected Agents:**
- BaseAgent default: 8000
- ContentCreator: 12000
- RendererSpec: 10000
- SectionPlanner: 8000
- SpecialSections: 18000

**Solution:** Set `BaseAgent.max_tokens = None` by default (let API use natural limits), remove all overrides.

---

## ISS-215: Job History Status Updates Not Displaying
**Status:** Open
**Priority:** Medium
**Description:** Status updates not showing properly on dashboard job history page. Need to investigate status polling and display logic.

---
