"""
Clean non-ASCII characters from Manim code files and re-render - FIXED PATHS
"""
from pathlib import Path
import subprocess
import shutil
import os

JOB_ID = "d76a0cc1"
JOB_DIR = Path(f"player/jobs/{JOB_ID}")
CODE_DIR = JOB_DIR / "manim_code"
VIDEOS_DIR = JOB_DIR / "videos"

# Manim outputs to project root media folder, not job folder
PROJECT_ROOT = Path(".")
MANIM_MEDIA = PROJECT_ROOT / "media" / "videos"

# Characters to replace
REPLACEMENTS = {
    '₹': 'Rs.',   # Rupee symbol
    '→': '->',    # Arrow
    '←': '<-',
    '↑': '^',
    '↓': 'v',
    '…': '...',   # Ellipsis
    '–': '-',     # En dash
    '—': '-',     # Em dash
    '"': '"',     # Smart quotes
    '"': '"',
    ''': "'",
    ''': "'",
    '•': '*',     # Bullet
    '×': 'x',     # Multiplication
    '÷': '/',     # Division
    '≈': '~',     # Approximately
    '≠': '!=',
    '≤': '<=',
    '≥': '>=',
    '°': ' deg',
    '²': '^2',
    '³': '^3',
    'π': 'pi',
}

def clean_text(text: str) -> str:
    """Remove or replace non-ASCII characters."""
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    
    # Remove remaining non-ASCII
    cleaned = ''.join(c if ord(c) < 128 else '' for c in text)
    return cleaned

def clean_and_render():
    print("=" * 60)
    print(f"CLEANING & RENDERING MANIM VIDEOS FOR JOB {JOB_ID}")
    print("=" * 60)
    
    VIDEOS_DIR.mkdir(exist_ok=True)
    
    code_files = sorted(CODE_DIR.glob("section_*.py"))
    print(f"\nFound {len(code_files)} Manim code files")
    print(f"Manim output folder: {MANIM_MEDIA.absolute()}")
    
    success = 0
    failed = 0
    
    for code_file in code_files:
        section_name = code_file.stem  # e.g., "section_10"
        final_output = VIDEOS_DIR / f"{section_name}.mp4"
        
        print(f"\n→ Processing {code_file.name}...")
        
        # Read and clean the file
        try:
            original = code_file.read_text(encoding='utf-8')
        except:
            original = code_file.read_text(encoding='latin-1')
        
        cleaned = clean_text(original)
        
        if original != cleaned:
            print(f"  Cleaned encoding issues")
            code_file.write_text(cleaned, encoding='utf-8')
        
        # Skip if already rendered successfully
        if final_output.exists() and final_output.stat().st_size > 50000:
            print(f"  Already rendered ({final_output.stat().st_size:,} bytes)")
            success += 1
            continue
        
        # Render from project root
        print(f"  Rendering...", end=" ", flush=True)
        
        try:
            result = subprocess.run(
                ["manim", "-ql", "--disable_caching", str(code_file), "MainScene"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(PROJECT_ROOT)  # Run from project root!
            )
            
            # Look for output at project root media folder
            # Pattern: media/videos/section_X/480p15/MainScene.mp4
            media_output = MANIM_MEDIA / section_name / "480p15" / "MainScene.mp4"
            
            if media_output.exists():
                shutil.copy(str(media_output), str(final_output))
                size = final_output.stat().st_size
                print(f"✅ Done ({size:,} bytes)")
                success += 1
            else:
                # Try to find it anywhere in media folder
                found = list(MANIM_MEDIA.rglob(f"*/480p15/MainScene.mp4"))
                for f in found:
                    if section_name in str(f.parent.parent):
                        shutil.copy(str(f), str(final_output))
                        size = final_output.stat().st_size
                        print(f"✅ Done ({size:,} bytes)")
                        success += 1
                        break
                else:
                    print(f"❌ No output at {media_output}")
                    if result.returncode != 0:
                        # Show last part of stderr
                        err = result.stderr[-300:] if result.stderr else ""
                        print(f"   {err}")
                    failed += 1
                
        except subprocess.TimeoutExpired:
            print(f"❌ Timeout")
            failed += 1
        except Exception as e:
            print(f"❌ {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"COMPLETE: {success} rendered, {failed} failed")
    print(f"{'='*60}")
    
    # List videos
    videos = sorted(VIDEOS_DIR.glob("section_*.mp4"))
    print(f"\nFinal videos ({len(videos)}):")
    for v in videos:
        print(f"  {v.name}: {v.stat().st_size:,} bytes")

if __name__ == "__main__":
    clean_and_render()
