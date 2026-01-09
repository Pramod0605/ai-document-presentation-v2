from pathlib import Path

def apply_fix():
    path = Path(r'render/manim/manim_runner.py')
    content = path.read_text(encoding='utf-8')
    
    # Target content to replace
    target = '''        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=tmpdir,
                env=env
            )'''
    
    # Replacement content
    replacement = '''        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
                cwd=tmpdir,
                env=env
            )'''
    
    if target in content:
        new_content = content.replace(target, replacement)
        path.write_text(new_content, encoding='utf-8')
        print("Successfully applied Unicode encoding fix to manim_runner.py")
    else:
        print("Target content not found in manim_runner.py")
        # Let's try to find just a part of it to be sure
        if 'result = subprocess.run(' in content:
            print("Found 'result = subprocess.run(', but exact match failed. Likely whitespace mismatch.")
            # More flexible search
            import re
            pattern = r'result = subprocess\.run\(\s*cmd,\s*capture_output=True,\s*text=True,'
            if re.search(pattern, content):
                print("Found pattern with regex.")
                new_content = re.sub(pattern, r'result = subprocess.run(\n                cmd,\n                capture_output=True,\n                text=True,\n                encoding="utf-8",', content)
                path.write_text(new_content, encoding='utf-8')
                print("Applied fix via regex.")

if __name__ == "__main__":
    apply_fix()
