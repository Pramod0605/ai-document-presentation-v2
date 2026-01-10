import os
import time
import requests
import logging
import json
from enum import Enum
from typing import Dict, Any, List, Optional
from core.latex_to_speech import latex_to_speech
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from core.analytics import AnalyticsTracker

logger = logging.getLogger(__name__)

class AvatarStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"

class AvatarGenerator:
    """
    Manages interaction with the Remote AI Avatar Generation API.
    """
    
    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or os.environ.get("AVATAR_API_URL")
        if not self.api_url:
            raise ValueError("AVATAR_API_URL environment variable is not set")
        
    def generate_avatar_video(self, text: str, job_id: str, section_id: int) -> Dict[str, Any]:
        """
        Submit a request to generate an avatar video for the given text.
        
        Args:
            text (str): The raw narration text (can contain LaTeX).
            job_id (str): The job ID for context.
            section_id (int): The section ID for context.
            
        Returns:
            Dict: Response containing 'task_id', 'status', etc.
        """
        # 1. Preprocess: Convert LaTeX using existing utility
        clean_text = latex_to_speech(text)
        logger.info(f"[AVATAR] Preprocessed text for Job {job_id}/Sec {section_id}: {clean_text[:50]}...")
        
        # 2. Submit to API
        try:
            url = f"{self.api_url}/generate"
            payload = {
                "text": clean_text
            }
            
            # 2. Submit to API with Retry Logic
            max_retries = 3
            backoff_factor = 2
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"[AVATAR] Submitting to {url} (Attempt {attempt + 1}/{max_retries})")
                    response = requests.post(url, data=payload, timeout=60) # Increased timeout
                    
                    if response.status_code in [200, 202]:
                        data = response.json()
                        task_id = data.get("task_id")
                        logger.info(f"[AVATAR] Task queued successfully: {task_id}")
                        return {
                            "task_id": task_id,
                            "status": "queued",
                            "clean_text": clean_text
                        }
                    elif response.status_code == 429: # Rate limit
                         wait = backoff_factor ** attempt
                         logger.warning(f"[AVATAR] Rate limited. Waiting {wait}s...")
                         time.sleep(wait)
                         continue
                    else:
                        logger.error(f"[AVATAR] API Error ({response.status_code}): {response.text}")
                        # Don't retry client errors (4xx) unless rate limit
                        if 400 <= response.status_code < 500:
                             return {"error": f"API Error: {response.text}", "status": "failed"}
                
                except requests.exceptions.RequestException as e:
                    logger.warning(f"[AVATAR] Network error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(backoff_factor ** attempt)
                    else:
                        logger.error(f"[AVATAR] Max retries exceeded.")
                        return {"error": str(e), "status": "failed"}

            return {"error": "Max retries exceeded", "status": "failed"}
                
        except Exception as e:
            logger.error(f"[AVATAR] Request failed: {e}")
            return {"error": str(e), "status": "failed"}

    def check_status(self, task_id: str) -> Dict[str, Any]:
        """
        Check the status of a specific avatar generation task.
        """
        try:
            url = f"{self.api_url}/status/{task_id}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Support both nested (old) and flat (new) structures
                if "task_status" in data:
                    status = data["task_status"].get("status")
                    output_url = data["task_status"].get("output")
                else:
                    status = data.get("status")
                    # Construct output URL from result.data.result_url if available
                    result_block = data.get("result", {})
                    output_url = None
                    if isinstance(result_block, dict):
                        inner_data = result_block.get("data", {})
                        if isinstance(inner_data, dict):
                             rel_url = inner_data.get("result_url")
                             if rel_url:
                                 base = self.api_url.replace("/api", "")
                                 output_url = f"{base}{rel_url}"

                return {
                    "status": status,
                    "progress_chunks": [],
                    "output_url": output_url,
                    "raw_response": data
                }
            return {"status": "unknown", "error": f"Status check failed: {response.status_code}"}
            
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def download_video(self, task_id: str, output_path: str) -> bool:
        """
        Download the completed video. 
        Note: We need the full output URL which comes from check_status.
        If we don't have it, we try the legacy download endpoint or construct it.
        """
        try:
            # 1. Get Status to find the URL
            status_info = self.check_status(task_id)
            download_url = status_info.get("output_url")
            
            # Fallback to legacy endpoint if no URL found
            if not download_url:
                 download_url = f"{self.api_url}/download/{task_id}"
            
            logger.info(f"[AVATAR] Downloading from {download_url} to {output_path}")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with requests.get(download_url, stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(output_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
            logger.info(f"[AVATAR] Download complete: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"[AVATAR] Download failed: {e}")
            return False

    def _update_artifacts(self, output_dir: str, section_id: int, video_path: str, duration: float = 0.0):
        """
        Live-patch presentation.json and analytics.json with the new avatar video.
        This is crucial for "Fire-and-Forget" mode where the main pipeline has already exited.
        """
        try:
            out_path = Path(output_dir)
            pres_path = out_path / "presentation.json"
            
            # 1. Update Presentation.json
            if pres_path.exists():
                try:
                    with open(pres_path, 'r', encoding='utf-8') as f:
                        pres_data = json.load(f)
                    
                    updated = False
                    for section in pres_data.get("sections", []):
                        if section.get("section_id") == section_id:
                            # Update video path (relative to output dir)
                            # Video is in output_dir/video_filename.mp4 -> we want just filename or relative path
                            if os.path.isabs(video_path):
                                try:
                                    rel_path = os.path.relpath(video_path, output_dir)
                                except ValueError:
                                    rel_path = os.path.basename(video_path)
                            else:
                                rel_path = os.path.basename(video_path)

                            # Player expects 'avatar_video' or 'video'
                            section["avatar_video"] = rel_path
                            section["avatar_status"] = "completed"
                            updated = True
                            break
                    
                    if updated:
                        with open(pres_path, 'w', encoding='utf-8') as f:
                            json.dump(pres_data, f, indent=2)
                        logger.info(f"[AVATAR] Updated presentation.json for Sec {section_id}")
                except Exception as e:
                    logger.error(f"[AVATAR] Failed to update presentation.json: {e}")

            # 2. Update Analytics.json (if exists)
            analytics_path = out_path / "analytics.json"
            if analytics_path.exists():
                try:
                    with open(analytics_path, 'r', encoding='utf-8') as f:
                        analytics = json.load(f)
                    
                    # Update counts
                    if "avatar" not in analytics:
                        analytics["avatar"] = {"successful_sections": 0, "section_details": [], "failed_sections": 0, "total_sections": 0}
                    
                    avatar_metrics = analytics["avatar"]
                    avatar_metrics["successful_sections"] = avatar_metrics.get("successful_sections", 0) + 1
                    
                    # Add detail
                    detail = {
                        "section_id": section_id,
                        "duration_seconds": round(duration, 2),
                        "status": "completed",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                    }
                    if "section_details" not in avatar_metrics:
                        avatar_metrics["section_details"] = []
                    avatar_metrics["section_details"].append(detail)
                    
                    with open(analytics_path, 'w', encoding='utf-8') as f:
                        json.dump(analytics, f, indent=2)
                    logger.info(f"[AVATAR] Updated analytics.json for Sec {section_id}")
                except Exception as e:
                    logger.error(f"[AVATAR] Failed to update analytics.json: {e}")

        except Exception as e:
            logger.error(f"[AVATAR] Critical error in _update_artifacts: {e}")

    def submit_parallel_job(self, presentation: Dict[str, Any], job_id: str, output_dir: str, tracker: Optional[AnalyticsTracker] = None) -> Dict[str, Any]:
        """
        Submits sections in strict batches of 2.
        For each batch:
          1. Submit 2 concurrent requests.
          2. Wait for BOTH to complete (polling).
          3. Download videos.
          4. Only then proceed to next batch.
        
        This respects the 2-GPU limit by ensuring we never have more than 2 tasks active.
        """
        logger.info(f"[AVATAR] Starting strict batch submission for Job {job_id}")
        sections = presentation.get("sections", [])
        total_sections = len(sections)
        
        # Initialize progress
        if tracker:
            tracker.update_progress(
                category="avatar_generation", 
                completed=0, 
                total=total_sections, 
                failed=0,
                message="Starting avatar generation..."
            )
        avatar_dir = Path(output_dir) / "avatars" # We might want to put them in root output_dir usually, but let's stick to existing pattern or caller's pref.
        # Check if caller expects them in root or subdir. 
        # Usually pipeline passes output_dir as job_dir. videos often go to output_dir directly or 'videos' subdir.
        # Let's verify where download_video saves them.
        # Actually existing code passed 'output_dir' meant as root.
        # Let's stick to saving in 'output_dir' (root of job) to match Player expectation of simple relative paths?
        # Re-reading existing code: 'avatar_dir = Path(output_dir) / "avatars"' was used in previous snippet.
        # If Player expects 'avatar.mp4' in root, we should maybe change this? 
        # But 'resolveMediaPath' in player checks multiple places. 
        # Let's stick to 'avatars' subdir to keep it clean, or root if simpler.
        # The prompt said "avatars appear in output folder".
        # Let's use root output_dir/videos to align with other videos? Or just output_dir.
        # Let's keep existing logic to minimize friction, but verify path.
        
        # Actually, let's look at what I wrote in the plan: "submit_parallel_job" logic.
        # I'll stick to the existing logic I wrote earlier:
        # "avatar_dir = Path(output_dir) / "avatars""
        
        avatar_dir = Path(output_dir)
        # NOTE: Changing to root or specific 'avatars' folder? 
        # Previous implementation I wrote used: avatar_dir = Path(output_dir) / "avatars"
        # But wait, if I put them in a subdir, I must ensure relatve path is correct for Player.
        # Using root is safer for simple 'video.mp4' links.
        # Let's use 'avatars' subdir for organization.
        
        save_dir = avatar_dir / "avatars"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "queued": [],
            "skipped": [],
            "failed": [],
            "completed": []
        }

        if not sections:
            print(f"[AVATAR] Warning: No sections found in presentation to process.")
            return results

        BATCH_SIZE = 2
        section_batches = [sections[i:i + BATCH_SIZE] for i in range(0, len(sections), BATCH_SIZE)]
        
        print(f"[AVATAR] Initiating synchronous processing in {len(section_batches)} batches...")
        
        # Helper to submit
        def _submit_single_section(section, job_id, save_dir):
            sec_id = section.get("section_id")
            output_filename = f"section_{sec_id}_avatar.mp4"
            output_path = save_dir / output_filename
            
            # 1. Check for existing
            if output_path.exists() and output_path.stat().st_size > 1000:
                return {"status": "skipped", "section_id": sec_id, "reason": "exists", "output_path": str(output_path)}

            # 2. Extract Text
            narration_text = ""
            if "narration_segments" in section: # V1.5 Preferred
                segments = section["narration_segments"]
                narration_text = " ".join([str(seg.get("text", "") or "") for seg in segments])
            elif "narration" in section:
                narr = section["narration"]
                if isinstance(narr, dict):
                    narration_text = narr.get("full_text", "")
                    if not narration_text:
                         narration_text = " ".join([str(s.get("text", "") or "") for s in narr.get("segments", [])])
                else:
                    narration_text = str(narr)
            
            if not narration_text or not narration_text.strip():
                return {"status": "skipped", "section_id": sec_id, "reason": "empty_text"}
            
            # 3. Submit
            print(f"[AVATAR] Submitting Sec {sec_id}...")
            res = self.generate_avatar_video(narration_text, job_id, sec_id)
            # Handle both task_id dict and direct error dict
            if "task_id" in res:
                return {
                    "status": "queued",
                    "section_id": sec_id,
                    "task_id": res["task_id"],
                    "output_path": str(output_path)
                }
            else:
                 return {"status": "failed", "section_id": sec_id, "error": res.get("error", "Unknown")}

        # --- BATCH LOOP ---
        for batch_idx, batch in enumerate(section_batches):
            print(f"\n[AVATAR] === Processing Batch {batch_idx + 1}/{len(section_batches)} (Size: {len(batch)}) ===")
            
            current_batch_tasks = []
            
            # 1. SUBMIT BATCH
            with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                futures = {executor.submit(_submit_single_section, sec, job_id, save_dir): sec for sec in batch}
                
                for future in as_completed(futures):
                    try:
                        res = future.result()
                        status = res.get("status")
                        if status == "queued":
                            current_batch_tasks.append(res)
                            results["queued"].append(res)
                        elif status == "skipped":
                            results["skipped"].append(res)
                            print(f"[AVATAR] - Sec {res.get('section_id')} skipped.")
                            if "output_path" in res:
                                 self._update_artifacts(output_dir, res["section_id"], res["output_path"])
                            if tracker:
                                tracker.update_progress(
                                    category="avatar_generation",
                                    completed=len(results["completed"]) + len(results["skipped"]),
                                    total=total_sections,
                                    failed=len(results["failed"]),
                                    message=f"Skipped Section {res.get('section_id')}"
                                )
                        else:
                            results["failed"].append(res)
                            print(f"[AVATAR] x Sec {res.get('section_id')} submission failed.")
                            if tracker:
                                tracker.update_progress(
                                    category="avatar_generation",
                                    completed=len(results["completed"]) + len(results["skipped"]),
                                    total=total_sections,
                                    failed=len(results["failed"]),
                                    message=f"Failed to submit Section {res.get('section_id')}"
                                )
                    except Exception as e:
                         print(f"[AVATAR] Submission Ex: {e}")
            
            if not current_batch_tasks:
                print(f"[AVATAR] Batch {batch_idx + 1} finished (No active tasks).")
                continue
                
            # 2. POLL & WAIT FOR BATCH
            print(f"[AVATAR] Waiting for {len(current_batch_tasks)} tasks to complete...")
            
            # Map task_id -> info
            active_map = {t["task_id"]: t for t in current_batch_tasks}
            completed_in_batch = set()
            
            # Timeout logic: e.g., 20 minutes max per batch
            start_wait = time.time()
            max_wait_sec = 1200 
            
            while len(completed_in_batch) < len(active_map):
                if time.time() - start_wait > max_wait_sec:
                    print(f"[AVATAR] TIMEOUT waiting for batch {batch_idx+1}.")
                    break
                
                # Check all active not yet completed
                pending_ids = [tid for tid in active_map if tid not in completed_in_batch]
                
                for tid in pending_ids:
                    status_res = self.check_status(tid)
                    status = status_res.get("status")
                    
                    if status == "completed":
                        print(f"[AVATAR] Task {tid} COMPLETED. Downloading...")
                        # Download immediately
                        out_path = active_map[tid]["output_path"]
                        success = self.download_video(tid, out_path)
                        
                        # Get duration from status if available
                        duration = 0.0
                        # Try to find duration in status_res
                        # status_res['raw_response']['result']['data']['video_duration']
                        try:
                            raw = status_res.get("raw_response", {})
                            duration = float(raw.get("result", {}).get("data", {}).get("video_duration", 0.0))
                        except:
                            pass

                        if success:
                            results["completed"].append(active_map[tid])
                            completed_in_batch.add(tid)
                            self._update_artifacts(output_dir, active_map[tid]["section_id"], out_path, duration)
                            
                            if tracker:
                                tracker.update_progress(
                                    category="avatar_generation",
                                    completed=len(results["completed"]) + len(results["skipped"]),
                                    total=total_sections,
                                    failed=len(results["failed"]),
                                    message=f"Completed Section {active_map[tid]['section_id']}"
                                )
                        else:
                            print(f"[AVATAR] Failed to download {tid}")
                            # Treat as completed (but failed download) to stop polling
                            completed_in_batch.add(tid) 
                            
                    elif status == "failed":
                        print(f"[AVATAR] Task {tid} FAILED on server.")
                        results["failed"].append(active_map[tid])
                        completed_in_batch.add(tid)
                        
                        if tracker:
                            tracker.update_progress(
                                category="avatar_generation",
                                completed=len(results["completed"]) + len(results["skipped"]),
                                total=total_sections,
                                failed=len(results["failed"]),
                                message=f"Task {tid} failed"
                            )
                    
                    # If 'queued' or 'processing', just wait
                
                if len(completed_in_batch) < len(active_map):
                    time.sleep(5) # Poll interval
            
            print(f"[AVATAR] Batch {batch_idx+1} Done.")
            
        final_msg = f"[AVATAR] Job Complete. Queued: {len(results['queued'])}, Completed/Downloaded: {len(results['completed'])}, Skipped: {len(results['skipped'])}"
        logger.info(final_msg)
        print(final_msg)
        return results
