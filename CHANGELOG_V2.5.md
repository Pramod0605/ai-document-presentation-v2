# Changelog - V2.5 Director Bible Enhancements

This update focuses on **Concurrency Safety**, **Stability**, and **Smart Recovery** for the presentation generation pipeline.

## 1. Concurrency & Sequential Safety (Global Job Pool)
- **Max Workers Enforced:** Reduced global concurrency to **2 parallel jobs** in `core/job_manager.py` for maximum stability.
- **Queued Retries:** All retry endpoints (Avatar, Manim, WAN, LTX) now use `job_manager.submit_task`.
  - *Previous Issue:* Retries spawned raw threads, bypassing the 2-job limit and causing "Thundering Herds".
  - *New Fix:* Retries now wait in the job queue, respecting the server's resource limits.
- **Sync Safety:** WAN generation in `core/pipeline_unified.py` is now synchronous to ensure worker slots are held correctly.

## 2. Smart Job Recovery
- **Goal:** Prevent loss of LLM progress during server restarts.
- **Mechanism:** On startup, `JobManager` now checks for `presentation.json` in interrupted jobs.
- **Action:** If found, the job is marked as **`completed_with_errors`** instead of `failed`.
- **User Benefit:** You no longer need to restart the entire pipeline; you can simply click "Retry" on the missing Avatar or Video sections from the Dashboard.

## 3. Asset Auto-Repair & Hotfixes
- **Asset Auto-Repair:** New endpoint `POST /api/repair-missing-assets/<job_id>` automatically restores missing avatars.
  - *Reliability:* It verifies the task status on the remote server before downloading.
  - *Cost Efficiency:* Re-downloads existing successful tasks; **no new billing/generation cost**.
- **Bulk Repair Script:** Added `scripts/repair_all_avatars.py` for one-click recovery of all historical jobs.
- **WAN Version Safety:** Implemented backward-compatibility for `submit_wan_background_job` to gracefully handle argument count mismatches during phased server updates.

## Files Modified
- `api/app.py`: Added `/api/repair-missing-assets/` and background task submission.
- `core/job_manager.py`: Implemented `_startup_cleanup` logic and `submit_task` pool management.
- `core/pipeline_unified.py`: Fixed `submit_wan_background_job` mismatch and enforced sync safety.
- `scripts/repair_all_avatars.py`: [NEW] Bulk recovery tool.
