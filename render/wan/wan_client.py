import os
import time
import requests
from pathlib import Path
from typing import Optional

KIE_API_KEY = os.environ.get("KIE_API_KEY", "")
KIE_API_URL = "https://api.kie.ai/api/v1/wan"

class WANClient:
    MAX_RETRIES = 3
    RETRY_DELAY = 5
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or KIE_API_KEY
        self.base_url = KIE_API_URL
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
        valid_durations = [5, 10, 15]
        if duration not in valid_durations:
            duration = 5 if duration <= 7 else (10 if duration <= 12 else 15)
        
        if not self.api_key:
            return self._generate_placeholder(prompt, duration, output_path)
        
        prompt = self._truncate_prompt(prompt, max_chars=800)
        
        try:
            create_response = requests.post(
                f"{self.base_url}/generate",
                headers=self.headers,
                json={
                    "model": "wan2.6-t2v",
                    "prompt": prompt,
                    "duration": duration,
                    "resolution": "720p",
                    "aspect_ratio": "16:9"
                },
                timeout=30
            )
            
            if create_response.status_code != 200:
                raise Exception(f"API creation failed: {create_response.status_code}")
            
            result = create_response.json()
            if result.get("code") != 200:
                raise Exception(f"API error: {result.get('msg', 'Unknown error')}")
            
            task_id = result.get("data", {}).get("taskId")
            
            if not task_id:
                raise Exception("No task ID returned from API")
            
            max_attempts = 60
            for attempt in range(max_attempts):
                status_response = requests.get(
                    f"{self.base_url}/record-detail?taskId={task_id}",
                    headers=self.headers,
                    timeout=30
                )
                
                if status_response.status_code == 200:
                    status_result = status_response.json()
                    if status_result.get("code") == 200:
                        status_data = status_result.get("data", {})
                        state = status_data.get("state", "")
                        
                        if state == "success":
                            video_info = status_data.get("videoInfo", {})
                            video_url = video_info.get("videoUrl")
                            if video_url:
                                return self._download_video(video_url, output_path)
                        elif state == "fail":
                            fail_msg = status_data.get("failMsg", "Unknown error")
                            raise Exception(f"Generation failed: {fail_msg}")
                        elif state in ["wait", "queueing", "generating"]:
                            print(f"[WAN 2.6] Status: {state}")
                
                time.sleep(5)
            
            raise Exception("Generation timed out after 60 attempts")
            
        except Exception as e:
            raise Exception(f"WAN API error: {e}")
    
    def _download_video(self, video_url: str, output_path: Optional[str]) -> str:
        response = requests.get(video_url, stream=True, timeout=120)
        if response.status_code == 200:
            output_path = output_path or f"runway_video_{int(time.time())}.mp4"
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return output_path
        raise Exception(f"Failed to download video: {response.status_code}")
    
    def _generate_placeholder(self, prompt: str, duration: int, output_path: Optional[str]) -> str:
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
            return output_path
            
        except Exception as e:
            print(f"Placeholder generation error: {e}")
            return self._create_ffmpeg_video(output_path, duration)
    
    def _create_ffmpeg_video(self, output_path: Optional[str], duration: int) -> str:
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
        
        print(f"[WAN] Prompt truncated from {len(prompt)} to {len(truncated)} chars")
        return truncated
