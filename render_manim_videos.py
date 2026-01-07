"""
Render all Manim code files for job d76a0cc1 - FIXED VERSION
"""
import subprocess
from pathlib import Path
import shutil

JOB_ID = "d76a0cc1"
JOB_DIR = Path(f"player/jobs/{JOB_ID}")
CODE_DIR = JOB_DIR / "manim_code"
VIDEOS_DIR = JOB_DIR / "videos"

def render_manim():
    print("=" * 60)
    print(f"RENDERING MANIM VIDEOS FOR JOB {JOB_ID}")
    print("=" * 60)
    
    VIDEOS_DIR.mkdir(exist_ok=True)
    
    code_files = sorted(CODE_DIR.glob("section_*.py"))
    print(f"\nFound {len(code_files)} Manim code files")
    
    success = 0
    failed = 0
    
    for code_file in code_files:
        section_num = code_file.stem.replace("section_", "")
        output_name = f"section_{section_num}.mp4"
        final_output = VIDEOS_DIR / output_name
        
        # Skip if already rendered
        if final_output.exists() and final_output.stat().st_size > 10000:
            print(f"→ {code_file.name}: Already exists ({final_output.stat().st_size:,} bytes)")
            success += 1
            continue
        
        print(f"→ Rendering {code_file.name}...", end=" ", flush=True)
        
        try:
            # Run manim with low quality for speed
            result = subprocess.run(
                [
                    "manim",
                    "-ql",  # Low quality (480p15fps) for faster rendering
                    "--disable_caching",
                    str(code_file),
                    "MainScene"
                ],
                capture_output=True,
                text=True,
                timeout=180,  # 3 minute timeout per video
                cwd=str(JOB_DIR)
            )
            
            # FIXED: Correct path - section_X/480p15/MainScene.mp4
            media_output = JOB_DIR / "media" / "videos" / code_file.stem / "480p15" / "MainScene.mp4"
            
            if media_output.exists():
                shutil.copy(str(media_output), str(final_output))
                size = final_output.stat().st_size
                print(f"✅ Done ({size:,} bytes)")
                success += 1
            else:
                print(f"❌ Output not found at {media_output}")
                if result.returncode != 0:
                    print(f"   Exit code: {result.returncode}")
                    # Show only actual errors, not sox warnings
                    errors = [l for l in result.stderr.split('\n') if 'Error' in l or 'Exception' in l]
                    if errors:
                        print(f"   Error: {errors[0][:150]}")
                failed += 1
                
        except subprocess.TimeoutExpired:
            print(f"❌ Timeout (>3 min)")
            failed += 1
        except Exception as e:
            print(f"❌ Error: {e}")
            failed += 1
    
    # Cleanup media folder
    media_dir = JOB_DIR / "media"
    if media_dir.exists():
        shutil.rmtree(media_dir, ignore_errors=True)
    
    print(f"\n{'='*60}")
    print(f"COMPLETE: {success} rendered, {failed} failed")
    print(f"Videos saved to: {VIDEOS_DIR}")
    print(f"{'='*60}")
    
    # List final videos
    print("\nFinal videos:")
    for v in sorted(VIDEOS_DIR.glob("section_*.mp4")):
        print(f"  {v.name}: {v.stat().st_size:,} bytes")

if __name__ == "__main__":
    render_manim()
