import os
import time
import requests
from pathlib import Path
from typing import Optional

KIE_API_KEY = os.environ.get("KIE_API_KEY", "")
KIE_API_URL = "https://api.kie.ai/api/v1/wan"

class WANClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or KIE_API_KEY
        self.base_url = KIE_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_video(self, prompt: str, duration: int = 5, output_path: Optional[str] = None) -> str:
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
                print(f"[WAN 2.6] API creation failed: {create_response.status_code}")
                return self._generate_placeholder(prompt, duration, output_path)
            
            result = create_response.json()
            if result.get("code") != 200:
                print(f"[WAN 2.6] API error: {result.get('msg', 'Unknown error')}")
                return self._generate_placeholder(prompt, duration, output_path)
            
            task_id = result.get("data", {}).get("taskId")
            
            if not task_id:
                print("[WAN 2.6] No task ID returned from API")
                return self._generate_placeholder(prompt, duration, output_path)
            
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
                            print(f"[WAN 2.6] Generation failed: {fail_msg}")
                            return self._generate_placeholder(prompt, duration, output_path)
                        elif state in ["wait", "queueing", "generating"]:
                            print(f"[WAN 2.6] Status: {state}")
                
                time.sleep(5)
            
            print("[WAN 2.6] Generation timed out")
            return self._generate_placeholder(prompt, duration, output_path)
            
        except Exception as e:
            print(f"[WAN 2.6] API error: {e}")
            return self._generate_placeholder(prompt, duration, output_path)
    
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
