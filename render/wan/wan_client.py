"""
WAN Video Client - Kie.ai WAN 2.6 Text-to-Video API
Updated: January 2026 to use new unified jobs API

Uses WAN 2.6 for variable duration support (5, 10, 15 seconds).
API Docs: https://docs.kie.ai/market/wan/2-6-text-to-video
"""
import os
import time
import json
import requests
from pathlib import Path
from typing import Optional

KIE_API_KEY = os.environ.get("KIE_API_KEY", "")
KIE_API_BASE = "https://api.kie.ai/api/v1"

class WANClient:
    MAX_RETRIES = 3
    RETRY_DELAY = 5
    POLL_INTERVAL = 5  # seconds between status checks
    MAX_POLL_ATTEMPTS = 120  # 10 minutes max wait (120 * 5s)
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or KIE_API_KEY
        self.base_url = KIE_API_BASE
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_video(self, prompt: str, duration: int = 5, output_path: Optional[str] = None, max_retries: Optional[int] = None) -> str:
        """Generate video with retry logic for transient failures."""
        retries = max_retries if max_retries is not None else self.MAX_RETRIES
        last_error = None
        
        for attempt in range(retries):
            try:
                result = self._generate_video_attempt(prompt, duration, output_path)
                if result and not result.endswith("_placeholder.mp4"):
                    return result
                last_error = "Placeholder generated instead of real video"
            except Exception as e:
                last_error = str(e)
                print(f"[WAN 2.6] Attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    print(f"[WAN 2.6] Retrying in {self.RETRY_DELAY}s...")
                    time.sleep(self.RETRY_DELAY)
        
        print(f"[WAN 2.6] All {retries} attempts failed, generating placeholder")
        return self._generate_placeholder(prompt, duration, output_path)
    
    def _generate_video_attempt(self, prompt: str, duration: int = 5, output_path: Optional[str] = None) -> str:
        """
        Single attempt to generate video using new Kie.ai unified jobs API.
        
        Uses WAN 2.6 for variable duration support (5, 10, 15 seconds).
        
        New API format (2026):
        POST /api/v1/jobs/createTask
        {
            "model": "wan/2-6-text-to-video",
            "input": {
                "prompt": "...",
                "duration": "5",  // "5", "10", or "15"
                "resolution": "720p"
            }
        }
        """
        if not self.api_key:
            print("[WAN 2.6] No API key configured, generating placeholder")
            return self._generate_placeholder(prompt, duration, output_path)
        
        # Truncate prompt to 800 chars max
        prompt = self._truncate_prompt(prompt, max_chars=800)
        
        # Normalize duration to valid WAN 2.6 values: 5, 10, or 15 seconds
        valid_durations = [5, 10, 15]
        if duration not in valid_durations:
            if duration <= 7:
                normalized_duration = 5
            elif duration <= 12:
                normalized_duration = 10
            else:
                normalized_duration = 15
            print(f"[WAN 2.6] Normalizing duration {duration}s -> {normalized_duration}s")
        else:
            normalized_duration = duration
        
        # Prepare request payload per new API spec - using WAN 2.6 for duration support
        payload = {
            "model": "wan/2-6-text-to-video",
            "input": {
                "prompt": prompt,
                "duration": str(normalized_duration),  # WAN 2.6 expects string
                "resolution": "720p"
            }
        }
        
        print(f"[WAN 2.6] Creating task (duration={normalized_duration}s): {prompt[:80]}...")
        
        try:
            # Step 1: Create the task
            create_response = requests.post(
                f"{self.base_url}/jobs/createTask",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            print(f"[WAN 2.6] Create response status: {create_response.status_code}")
            
            if create_response.status_code != 200:
                error_text = create_response.text[:500] if create_response.text else "No response body"
                raise Exception(f"API creation failed: {create_response.status_code} - {error_text}")
            
            result = create_response.json()
            
            if result.get("code") != 200:
                raise Exception(f"API error: {result.get('msg', result.get('message', 'Unknown error'))}")
            
            task_id = result.get("data", {}).get("taskId")
            
            if not task_id:
                raise Exception(f"No task ID returned from API. Response: {result}")
            
            print(f"[WAN 2.6] Task created: {task_id}")
            
            # Step 2: Poll for completion using unified recordInfo endpoint
            video_url = self._poll_task_status(task_id)
            
            if not video_url:
                raise Exception("Task completed but no video URL returned")
            
            # Step 3: Download the video
            return self._download_video(video_url, output_path)
            
        except requests.exceptions.Timeout:
            raise Exception("API request timed out")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Connection error: {e}")
        except Exception as e:
            raise Exception(f"WAN API error: {e}")
    
    def _poll_task_status(self, task_id: str) -> Optional[str]:
        """
        Poll task status using unified /jobs/recordInfo endpoint.
        
        States: waiting, queuing, generating, success, fail
        On success, resultJson contains {"resultUrls": ["url1", ...]}
        """
        print(f"[WAN 2.6] Polling task status for {task_id}...")
        
        for attempt in range(self.MAX_POLL_ATTEMPTS):
            try:
                status_response = requests.get(
                    f"{self.base_url}/jobs/recordInfo",
                    headers=self.headers,
                    params={"taskId": task_id},
                    timeout=30
                )
                
                if status_response.status_code != 200:
                    print(f"[WAN 2.6] Status check failed: {status_response.status_code}")
                    time.sleep(self.POLL_INTERVAL)
                    continue
                
                status_result = status_response.json()
                
                if status_result.get("code") != 200:
                    print(f"[WAN 2.6] Status API error: {status_result.get('msg', 'Unknown')}")
                    time.sleep(self.POLL_INTERVAL)
                    continue
                
                data = status_result.get("data", {})
                state = data.get("state", "")
                
                print(f"[WAN 2.6] Poll {attempt + 1}/{self.MAX_POLL_ATTEMPTS}: state={state}")
                
                if state == "success":
                    # Parse resultJson to get video URLs
                    result_json_str = data.get("resultJson", "{}")
                    try:
                        result_json = json.loads(result_json_str) if isinstance(result_json_str, str) else result_json_str
                        result_urls = result_json.get("resultUrls", [])
                        if result_urls:
                            print(f"[WAN 2.6] Video ready: {result_urls[0][:80]}...")
                            return result_urls[0]
                        else:
                            raise Exception("Success state but no resultUrls found")
                    except json.JSONDecodeError as e:
                        raise Exception(f"Failed to parse resultJson: {e}")
                
                elif state == "fail":
                    fail_msg = data.get("failMsg", "Unknown error")
                    fail_code = data.get("failCode", "")
                    raise Exception(f"Generation failed: [{fail_code}] {fail_msg}")
                
                elif state in ["waiting", "queuing", "generating"]:
                    # Still processing, continue polling
                    pass
                else:
                    print(f"[WAN 2.6] Unknown state: {state}")
                
            except requests.exceptions.RequestException as e:
                print(f"[WAN 2.6] Poll request failed: {e}")
            
            time.sleep(self.POLL_INTERVAL)
        
        raise Exception(f"Task timed out after {self.MAX_POLL_ATTEMPTS * self.POLL_INTERVAL}s")
    
    def _download_video(self, video_url: str, output_path: Optional[str]) -> str:
        """Download video from URL to local file."""
        print(f"[WAN 2.6] Downloading video...")
        
        response = requests.get(video_url, stream=True, timeout=120)
        if response.status_code == 200:
            output_path = output_path or f"wan_video_{int(time.time())}.mp4"
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[WAN 2.6] Video saved to: {output_path}")
            return output_path
        raise Exception(f"Failed to download video: {response.status_code}")
    
    def _generate_placeholder(self, prompt: str, duration: int, output_path: Optional[str]) -> str:
        """Generate placeholder video when API fails or is not configured."""
        try:
            from moviepy import ColorClip
            
            output_path = output_path or f"placeholder_{int(time.time())}.mp4"
            
            bg = ColorClip(size=(1280, 720), color=(30, 30, 60), duration=duration)
            
            bg.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio=False,
                logger=None
            )
            
            bg.close()
            print(f"[WAN 2.2] Placeholder saved to: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Placeholder generation error: {e}")
            return self._create_ffmpeg_video(output_path, duration)
    
    def _create_ffmpeg_video(self, output_path: Optional[str], duration: int) -> str:
        """Fallback: create video using ffmpeg directly."""
        import subprocess
        
        output_path = output_path or f"minimal_{int(time.time())}.mp4"
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=0x1e3c72:s=1280x720:d={duration}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            output_path
        ]
        subprocess.run(cmd, capture_output=True)
        return output_path
    
    def _truncate_prompt(self, prompt: str, max_chars: int = 800) -> str:
        """Truncate prompt to max_chars at sentence boundary if possible."""
        if len(prompt) <= max_chars:
            return prompt
        
        truncated = prompt[:max_chars]
        last_period = truncated.rfind('.')
        if last_period > max_chars * 0.6:
            truncated = truncated[:last_period + 1]
        
        print(f"[WAN 2.2] Prompt truncated from {len(prompt)} to {len(truncated)} chars")
        return truncated
