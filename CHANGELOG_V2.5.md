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

## 3. Bug Fixes & Improvements
- **Duplicate Avatar Trigger:** Removed redundant trigger in `pipeline_unified.py` to prevent race conditions and double-billing.
- **Accurate Status Logs:** Jobs now report granular phases (`Generating Video...`, `Generating Avatars...`, `LLM Completed_Processing_Assets`) to prevent the dashboard from prematurely showing green.
- **Result Preservation:** Ensured `presentation.json` is persisted before asset generation starts so metadata is available even during background processing.

## Files Modified
- `api/app.py`: Implemented background task submission for all retry types.
- `core/job_manager.py`: Implemented `_startup_cleanup` logic and `submit_task` pool management.
- `core/pipeline_unified.py`: Enforced sync safety for WAN generation and removed duplicate triggers.
- `core/renderer_executor.py`: Updated status reporting and renderer selection logic.
