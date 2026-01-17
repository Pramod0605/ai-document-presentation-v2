import os
import time
import logging
import asyncio
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from render.wan.wan_client import WANClient

logger = logging.getLogger(__name__)

class KieBatchGenerator:
    """
    Batched generator for Kie.ai WAN API.
    Handles rate limits (15 concurrent, 15s interval) and parallel polling.
    """
    
    BATCH_SIZE = 15
    BATCH_INTERVAL = 15
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = WANClient(api_key)
        self.pending_tasks = [] # List of (beat_id, task_id, output_path)
    
    def generate_batch(self, beats: List[Dict], output_dir: str):
        """
        Process a list of beats in batches.
        Each beat in 'beats' should have: beat_id, prompt, duration_hint
        """
        if not beats:
            return {}
            
        os.makedirs(output_dir, exist_ok=True)
        results = {}
        
        # 1. Submission Phase
        for i in range(0, len(beats), self.BATCH_SIZE):
            batch = beats[i:i + self.BATCH_SIZE]
            logger.info(f"[KieBatch] Submitting batch {i // self.BATCH_SIZE + 1} ({len(batch)} items)...")
            
            for beat in batch:
                beat_id = beat.get("beat_id")
                prompt = beat.get("prompt")
                duration = int(beat.get("duration_hint", 15))
                output_path = os.path.join(output_dir, f"{beat_id}.mp4")
                
                print(f"[WAN] Submitting Beat: {beat_id} | Prompt: {prompt[:60]}... | Duration: {duration}s")
                try:
                    # We use a modified client or just extract the create logic
                    # For now, let's use the client's internal methods (or refactor client)
                    # REFINE: Refactor WANClient to expose createTask separately
                    task_id = self._create_task(prompt, duration)
                    if task_id:
                        self.pending_tasks.append({
                            "beat_id": beat_id,
                            "task_id": task_id,
                            "output_path": output_path,
                            "prompt": prompt,
                            "duration": duration
                        })
                    else:
                        logger.error(f"[KieBatch] Failed to create task for {beat_id}")
                except Exception as e:
                    logger.error(f"[KieBatch] Submission error for {beat_id}: {e}")
            
            # Rate limit wait between batches
            if i + self.BATCH_SIZE < len(beats):
                logger.info(f"[KieBatch] Waiting {self.BATCH_INTERVAL}s before next batch...")
                time.sleep(self.BATCH_INTERVAL)
        
        # 2. Polling Phase
        logger.info(f"[KieBatch] Polling {len(self.pending_tasks)} tasks...")
        results = self._poll_all_tasks()
        
        return results

    def _create_task(self, prompt: str, duration: int) -> Optional[str]:
        """Submit a single task to Kie.ai and return task_id."""
        import requests
        
        # Normalize duration
        valid_durations = [5, 10, 15]
        normalized_duration = 15
        if duration <= 7: normalized_duration = 5
        elif duration <= 12: normalized_duration = 10
        
        # Truncate prompt
        truncated_prompt = self.client._truncate_prompt(prompt, max_chars=800)
        
        payload = {
            "model": "wan/2-6-text-to-video",
            "input": {
                "prompt": truncated_prompt,
                "duration": str(normalized_duration),
                "resolution": "720p",
                "aspect_ratio": "16:9",
                "negative_prompt": "blurry, low quality, distorted, text overlay, watermark"
            }
        }
        
        try:
            response = requests.post(
                f"{self.client.base_url}/jobs/createTask",
                headers=self.client.headers,
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("code") == 200:
                    return res_json.get("data", {}).get("taskId")
            logger.error(f"[KieBatch] API returned {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"[KieBatch] CreateTask Exception: {e}")
        return None

    def _poll_all_tasks(self) -> Dict:
        """Poll all tasks in parallel using a thread pool."""
        final_results = {}
        print(f"[WAN] Starting parallel polling for {len(self.pending_tasks)} tasks...")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_beat = {
                executor.submit(self._poll_and_download, task): task["beat_id"] 
                for task in self.pending_tasks
            }
            
            for future in as_completed(future_to_beat):
                beat_id = future_to_beat[future]
                try:
                    local_path = future.result()
                    final_results[beat_id] = local_path
                except Exception as e:
                    logger.error(f"[KieBatch] Task {beat_id} failed: {e}")
                    final_results[beat_id] = None # Or handle placeholder
                    
        return final_results

    def _poll_and_download(self, task_info: Dict) -> str:
        """Poller for a single task."""
        task_id = task_info["task_id"]
        output_path = task_info["output_path"]
        
        # Use client's polling and download methods
        video_url = self.client._poll_task_status(task_id)
        if video_url:
            return self.client._download_video(video_url, output_path)
        
        # If failed, generate placeholder
        return self.client._generate_placeholder(task_info["prompt"], task_info["duration"], output_path)
