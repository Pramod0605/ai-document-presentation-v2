
import sys
from pathlib import Path

def check_pointers():
    path = Path(r"player/jobs/2d8a9c39/source_markdown.md")
    if not path.exists():
        print(f"File not found: {path}")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    target = "An **Arithmetic Progression (AP)** is a list"
    
    print(f"\n--- Checking Pointer Fidelity ---")
    print(f"Looking for: '{target}'")
    
    if target in content:
        print("✅ EXACT MATCH FOUND!")
    else:
        print("❌ MATCH FAILED.")
        # Find close matches
        import difflib
        # Look for the substring "Arithmetic Progression (AP)"
        idx = content.find("Arithmetic Progression (AP)")
        if idx != -1:
             start = max(0, idx - 20)
             end = min(len(content), idx + 100)
             snippet = content[start:end]
             print(f"Found in source (context):\n...{snippet}...")
             print(f"Values:")
             print(f"  Target: {target}")
             print(f"  Source: {snippet.split('is a list')[0]}is a list")
        else:
            print("String not found at all.")

if __name__ == "__main__":
    check_pointers()
