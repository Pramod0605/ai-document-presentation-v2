import os
import time
import logging
import asyncio
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from render.wan.wan_client import WANClient, WanSafetyError, WanFatalError
from core.llm_client import openrouter

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

    def _rewrite_prompt(self, original_prompt: str, feedback: str = None, is_safety_fix: bool = False) -> str:
        """Rewrite prompt using LLM for safety or user feedback."""
        try:
            # HARD SAFETY RULES for System Prompt
            safety_rules = """
🔒 WAN VIDEO PROMPT HARD SAFETY RULES (MANDATORY)
1. NEVER use close-up or extreme framing for humans.
   - DO NOT use: "close-up", "extreme close-up", "macro", "tight framing"
   - ALWAYS use: "medium shot", "medium-wide shot", or "wide shot"
2. NEVER explicitly mention human body parts.
   - DO NOT mention: hands, eyes, face, skin, fingers
   - Describe actions indirectly (e.g., "writing at a desk", "focused posture")
3. NEVER use age-descriptive human terms.
   - DO NOT use: young, child, girl, boy, young woman
   - ALWAYS use: "adult person" or "individual"
4. NEVER use cinematic intimacy language.
   - DO NOT use: rack focus, lingering shot, intimate, sensual, dramatic zoom on person
   - Use neutral camera behavior: steady camera, fixed framing, gentle focus shift
5. Style disclaimers DO NOT override safety.
   - Phrases like "educational", "documentary", or "non-sexual" do NOT make unsafe prompts valid.
"""
            if is_safety_fix:
                sys_prompt = f"You are a safety assistant. Rewrite this video prompt to be safe, educational, and documentary-style. remove any potential NSFW triggers. Follow these HARD SAFETY RULES:{safety_rules} Return ONLY the new prompt."
            elif feedback:
                sys_prompt = f"You are a video prompt improver. Rewrite this prompt to incorporate the user's feedback: '{feedback}'. Keep it safe and documentary-style. Return ONLY the new prompt."
            else:
                return original_prompt

            response = openrouter.chat.completions.create(
                model="google/gemini-2.5-flash", # Fast model for rewrites
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": original_prompt}
                ]
            )
            new_prompt = response.choices[0].message.content.strip()
            # Remove quotes if present
            if new_prompt.startswith('"') and new_prompt.endswith('"'):
                new_prompt = new_prompt[1:-1]
            logger.info(f"[WAN Safety] Prompt rewritten: '{original_prompt[:30]}...' -> '{new_prompt[:30]}...'")
            return new_prompt
        except Exception as e:
            logger.error(f"[WAN Safety] LLM Rewrite failed: {e}")
            return original_prompt # Fallback
    
    def generate_batch(self, beats: List[Dict], output_dir: str, user_feedback: str = None):
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
                original_prompt = beat.get("prompt")
                # TODO: In future, support 'duration' key as well. For now, rely on duration_hint or default 15.
                duration = int(beat.get("duration_hint", 15))
                output_path = os.path.join(output_dir, f"{beat_id}.mp4")
                
                # GRANULAR RETRY: Check if file exists and is valid (>0 bytes)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    print(f"[WAN] Skipping existing beat: {beat_id}")
                    # Pre-populate result immediately so it's returned at the end
                    results[beat_id] = output_path 
                    continue
                
                # Pre-process prompt if user feedback provided
                current_prompt = original_prompt
                if user_feedback:
                    logger.info(f"[WAN] Applying user feedback to prompt for {beat_id}")
                    current_prompt = self._rewrite_prompt(original_prompt, feedback=user_feedback)

                print(f"[WAN] Submitting Beat: {beat_id} | Prompt: {current_prompt[:60]}... | Duration: {duration}s")
                
                try:
                    # Attempt 1
                    task_id = self._create_task(current_prompt, duration)
                    if task_id:
                        self.pending_tasks.append({
                            "beat_id": beat_id,
                            "task_id": task_id,
                            "output_path": output_path,
                            "prompt": current_prompt,
                            "duration": duration
                        })
                    else:
                        logger.error(f"[KieBatch] Failed to create task for {beat_id}")

                except WanSafetyError as e:
                    logger.warning(f"[WAN] Safety Error for {beat_id}: {e}. Retrying with LLM rewrite...")
                    # Rewrite for safety
                    safe_prompt = self._rewrite_prompt(current_prompt, is_safety_fix=True)
                    try:
                        # Attempt 2 (Retry once)
                        task_id = self._create_task(safe_prompt, duration)
                        if task_id:
                            self.pending_tasks.append({
                                "beat_id": beat_id,
                                "task_id": task_id,
                                "output_path": output_path,
                                "prompt": safe_prompt,
                                "duration": duration
                            })
                            logger.info(f"[WAN] Safety retry submitted for {beat_id}")
                        else:
                            logger.error(f"[WAN] Safety retry failed to create task for {beat_id}")
                    except Exception as retry_e:
                        logger.error(f"[WAN] Safety retry FAILED for {beat_id}: {retry_e}")
                        
                except WanFatalError as e:
                    logger.error(f"[WAN] Fatal Error for {beat_id}: {e}. Skipping retry.")
                
                except Exception as e:
                    logger.error(f"[KieBatch] Submission error for {beat_id}: {e}")
            
            # Rate limit wait between batches
            if i + self.BATCH_SIZE < len(beats):
                logger.info(f"[KieBatch] Waiting {self.BATCH_INTERVAL}s before next batch...")
                time.sleep(self.BATCH_INTERVAL)
        
        # 2. Polling Phase
        if self.pending_tasks:
            logger.info(f"[KieBatch] Polling {len(self.pending_tasks)} tasks...")
            polled_results = self._poll_all_tasks()
            results.update(polled_results)
        else:
            logger.info("[KieBatch] No pending tasks to poll.")
        
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

            # --- ERROR MAPPING (Replicated from WANClient) ---
            if response.status_code in [422, 403, 451]:
                raise WanSafetyError(f"Safety/Policy Violation ({response.status_code}): {response.text}")
            
            if response.status_code in [401, 402, 404]:
                raise WanFatalError(f"Fatal API Error ({response.status_code}): {response.text}")

            if response.status_code == 400:
                err_text = response.text.lower()
                if "nsfw" in err_text or "policy" in err_text or "safety" in err_text:
                    raise WanSafetyError(f"Safety Violation (400): {response.text}")
                else:
                    raise WanFatalError(f"Bad Request (400): {response.text}")
            # ------------------------------------------------

            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("code") == 200:
                    return res_json.get("data", {}).get("taskId")
                else:
                    logger.error(f"[KieBatch] API Logic Error: {res_json}")
            else:
                logger.error(f"[KieBatch] API returned {response.status_code}: {response.text}")
                
        except (WanSafetyError, WanFatalError) as e:
            raise e # Propagate to generate_batch for retry handling logic
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
