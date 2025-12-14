import os
import time
import requests
from pathlib import Path

KIE_API_KEY = os.environ.get("KIE_API_KEY", "")
KIE_API_URL = "https://api.kie.ai/v1"

class WANClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or KIE_API_KEY
        self.base_url = KIE_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_video(self, prompt: str, duration: int = 5, output_path: str = None) -> str:
        if not self.api_key:
            return self._generate_placeholder(prompt, duration, output_path)
        
        try:
            create_response = requests.post(
                f"{self.base_url}/generations",
                headers=self.headers,
                json={
                    "model": "wan",
                    "prompt": prompt,
                    "duration": duration,
                    "aspect_ratio": "16:9",
                    "quality": "high"
                },
                timeout=30
            )
            
            if create_response.status_code != 200:
                print(f"WAN API creation failed: {create_response.status_code}")
                return self._generate_placeholder(prompt, duration, output_path)
            
            task_data = create_response.json()
            task_id = task_data.get("id") or task_data.get("task_id")
            
            if not task_id:
                return self._generate_placeholder(prompt, duration, output_path)
            
            max_attempts = 60
            for attempt in range(max_attempts):
                status_response = requests.get(
                    f"{self.base_url}/generations/{task_id}",
                    headers=self.headers,
                    timeout=30
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get("status", "")
                    
                    if status == "completed":
                        video_url = status_data.get("video_url") or status_data.get("output", {}).get("video_url")
                        if video_url:
                            return self._download_video(video_url, output_path)
                    elif status == "failed":
                        print(f"WAN generation failed: {status_data.get('error', 'Unknown error')}")
                        return self._generate_placeholder(prompt, duration, output_path)
                
                time.sleep(5)
            
            print("WAN generation timed out")
            return self._generate_placeholder(prompt, duration, output_path)
            
        except Exception as e:
            print(f"WAN API error: {e}")
            return self._generate_placeholder(prompt, duration, output_path)
    
    def _download_video(self, video_url: str, output_path: str) -> str:
        response = requests.get(video_url, stream=True, timeout=120)
        if response.status_code == 200:
            output_path = output_path or f"wan_video_{int(time.time())}.mp4"
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return output_path
        raise Exception(f"Failed to download video: {response.status_code}")
    
    def _generate_placeholder(self, prompt: str, duration: int, output_path: str) -> str:
        try:
            from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
            
            output_path = output_path or f"placeholder_{int(time.time())}.mp4"
            
            bg = ColorClip(size=(1280, 720), color=(30, 30, 60), duration=duration)
            
            try:
                txt = TextClip(
                    prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    fontsize=24,
                    color="white",
                    size=(1200, None),
                    method="caption"
                )
                txt = txt.set_position("center").set_duration(duration)
                video = CompositeVideoClip([bg, txt])
            except Exception:
                video = bg
            
            video.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio=False,
                verbose=False,
                logger=None
            )
            
            video.close()
            return output_path
            
        except Exception as e:
            print(f"Placeholder generation error: {e}")
            return self._create_minimal_video(output_path, duration)
    
    def _create_minimal_video(self, output_path: str, duration: int) -> str:
        from moviepy.editor import ColorClip
        
        output_path = output_path or f"minimal_{int(time.time())}.mp4"
        clip = ColorClip(size=(1280, 720), color=(40, 40, 80), duration=duration)
        clip.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio=False,
            verbose=False,
            logger=None
        )
        clip.close()
        return output_path
