# Issue Tracker

## Active Issues

### ISS-161: WAN Video Prompts Lost (5 → 1)
**Status**: Open  
**Discovered**: 2024-12-26  
**Severity**: Critical  

**Problem**: Recap section's 5 video_prompts are being concatenated into one 3551-char prompt, which gets truncated to 800 chars, resulting in only 1 video being generated instead of 5.

**Root Cause**: Pipeline mismatch in `wan_runner.py`:
1. RecapAgent outputs `video_prompts: [5 beats]` (649-740 chars each, within limits)
2. `renderer_executor.py` concatenates them into `compiled_wan_prompt` 
3. `wan_runner.py` line 64 checks for `recap_scenes` (empty!) and skips multi-scene mode
4. Falls through to single-prompt mode → 3551 chars → truncated to 800 chars

**Expected Behavior**: 5 separate kie.ai API calls, each with ~700 char prompt, generating 5 videos

**Files Affected**:
- `render/wan/wan_runner.py` - needs to handle `video_prompts` for recap sections
- `core/renderer_executor.py` - concatenation logic

**Fix**: Add handling for recap sections with `video_prompts` (not just `recap_scenes`)

---

### ISS-162: Content Sections Have segments:0
**Status**: Open  
**Discovered**: 2024-12-26  
**Severity**: High  

**Problem**: Content sections in presentation.json have `visual_beats: 8` but `segments: 0`. The player expects segments for narration/visual timing.

**Evidence**:
```json
{
  "section_type": "content",
  "visual_beats": [8 beats],
  "segments": []  // Empty!
}
```

**Root Cause**: TBD - Need to trace where segments should be populated from narration output

**Expected Behavior**: Each section should have segments array with:
- narration text
- duration_seconds
- visual_content (from visual_beats)
- display_directives

**Files to Check**:
- `core/pipeline_v15.py` - merge step
- `core/agents/narration_writer.py`

---

### ISS-163: kie.ai Internal Error (topic_10.mp4)
**Status**: Open  
**Discovered**: 2024-12-26  
**Severity**: Medium  

**Problem**: kie.ai returned "internal error" for recap video, but code reported "Success". The resulting topic_10.mp4 is only 14KB (should be 500KB-1MB).

**Evidence**:
```
Runway generation failed: internal error, please try again later.
  -> Success: /home/runner/workspace/player/jobs/fb4d4d7a/videos/topic_10.mp4
```

**Root Cause**: Error handling in WAN client not properly detecting API failures

**Files Affected**:
- `render/wan/wan_client.py` - error handling

---

## Resolved Issues

(None yet)
