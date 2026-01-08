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
        self.api_url = api_url or os.environ.get("AVATAR_API_URL", "http://69.197.145.4:5001/api")
        self.default_mode = os.environ.get("AVATAR_DEFAULT_MODE", "chunked_parallel_async")
        
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
                    
                    if response.status_code == 200:
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
                # API returns 'task_status': {'status': 'completed', ...} inside root
                task_info = data.get("task_status", {})
                status = task_info.get("status", "unknown")
                return {
                    "status": status,
                    "progress_chunks": task_info.get("chunks", []),
                    "output_url": task_info.get("output"),
                    "raw_response": data
                }
            return {"status": "unknown", "error": f"Status check failed: {response.status_code}"}
            
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def download_video(self, task_id: str, output_path: str) -> bool:
        """
        Download the completed video to the specified path.
        """
        try:
            url = f"{self.api_url}/download/{task_id}"
            logger.info(f"[AVATAR] Downloading from {url} to {output_path}")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with requests.get(url, stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(output_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
            logger.info(f"[AVATAR] Download complete: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"[AVATAR] Download failed: {e}")
            return False
    def submit_parallel_job(self, presentation: Dict[str, Any], job_id: str, output_dir: str) -> Dict[str, Any]:
        """
        Submits all valid sections in the presentation to the Avatar API concurrently.
        
        Features:
        - Concurrency: Uses ThreadPoolExecutor (10 workers)
        - Smart Retry: Skips sections where video already exists
        - Fault Tolerance: Individual failures don't stop the batch
        
        Returns:
            Dict summary of submissions (queued, skipped, failed)
        """
        logger.info(f"[AVATAR] Starting parallel submission for Job {job_id}")
        sections = presentation.get("sections", [])
        avatar_dir = Path(output_dir) / "avatars"
        avatar_dir.mkdir(parents=True, exist_ok=True)
        
        active_tasks = []
        skipped_count = 0
        failed_count = 0
        
        def _submit_single_section(section, job_id, avatar_dir):
            sec_id = section.get("section_id")
            
            # 1. Check for existing video (Smart Retry)
            output_filename = f"section_{sec_id}_avatar.mp4"
            output_path = avatar_dir / output_filename
            
            if output_path.exists() and output_path.stat().st_size > 1000:
                logger.debug(f"[AVATAR] Skipping Section {sec_id} - Video exists")
                return {"status": "skipped", "section_id": sec_id}
                
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
            
            # UNIQUE CONFIRMATION LOGGING
            snippet = narration_text[:100].replace('\n', ' ')
            print(f"[AVATAR] Submitting Sec {sec_id}: '{snippet}...' ({len(narration_text)} chars)")
            logger.info(f"[AVATAR] Submission text for Sec {sec_id}: {snippet}...")
            
            # 3. Submit
            res = self.generate_avatar_video(narration_text, job_id, sec_id)
            if "task_id" in res:
                return {
                    "status": "queued",
                    "section_id": sec_id,
                    "task_id": res["task_id"]
                }
            else:
                 return {
                    "status": "failed", 
                    "section_id": sec_id, 
                    "error": res.get("error", "Unknown")
                }

        results = {
            "queued": [],
            "skipped": [],
            "failed": []
        }

        if not sections:
            print(f"[AVATAR] Warning: No sections found in presentation to process.")
            return results

        # Concurrency: 2 Workers at a time per user request
        BATCH_SIZE = 2
        section_batches = [sections[i:i + BATCH_SIZE] for i in range(0, len(sections), BATCH_SIZE)]
        
        print(f"[AVATAR] Initiating throttled submission in {len(section_batches)} batches of {BATCH_SIZE}...")
        
        for batch_idx, batch in enumerate(section_batches):
            print(f"[AVATAR] Processing Batch {batch_idx + 1}/{len(section_batches)}...")
            with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                future_to_sec = {
                    executor.submit(_submit_single_section, sec, job_id, avatar_dir): sec 
                    for sec in batch
                }
                
                for future in as_completed(future_to_sec):
                    try:
                        res = future.result()
                        status = res.get("status")
                        sec_id = res.get("section_id")
                        
                        if status == "queued":
                            results["queued"].append(res)
                            msg = f"[AVATAR] ✓ Section {sec_id} queued (Task: {res['task_id']})"
                            logger.info(msg)
                            print(msg)
                        elif status == "skipped":
                            results["skipped"].append(res)
                            skipped_count += 1
                            print(f"[AVATAR] - Section {sec_id} skipped ({res.get('reason', 'exists')})")
                        else:
                            results["failed"].append(res)
                            failed_count += 1
                            msg = f"[AVATAR] ✗ Section {sec_id} failed: {res.get('error')}"
                            logger.error(msg)
                            print(msg)
                            
                    except Exception as e:
                        print(f"[AVATAR] ✗ Thread Exception: {e}")
                        logger.error(f"[AVATAR] Thread Exception: {e}")
                        failed_count += 1
            
            if batch_idx < len(section_batches) - 1:
                wait_time = 2
                print(f"[AVATAR] Batch {batch_idx + 1} complete. Waiting {wait_time}s to avoid rate limits...")
                time.sleep(wait_time)
        
        final_msg = f"[AVATAR] Submission Complete for Job {job_id}: {len(results['queued'])} queued, {skipped_count} skipped, {failed_count} failed"
        logger.info(final_msg)
        print(final_msg)
        return results
