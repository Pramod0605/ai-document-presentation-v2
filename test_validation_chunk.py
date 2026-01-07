
import json
import sys
from pathlib import Path
from core.validators.v25_validator import V25Validator

def test_chunk():
    # Load Debug JSON
    try:
        with open("debug_llm_chunk_2_attempt_0.txt", "r", encoding="utf-8") as f:
            raw = f.read()
            # If it wrapped in markdown block, clean it
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            data = json.loads(raw)
    except Exception as e:
        print(f"Failed to load debug json: {e}")
        return

    # Load Source MD
    try:
        # 2. Load the Source Markdown
        source_md_file = "player/jobs/83ad0c3f/source_markdown.md"
        with open(source_md_file, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        print(f"Failed to load source md: {e}")
        return

    with open("test_results.txt", "w", encoding="utf-8") as f:
        f.write("--- Running V25Validator on Chunk 2 ---\n")
        
        errors = V25Validator.validate_content_chunk(data, source)
        
        if errors:
            f.write("❌ Validation Errors:\n")
            for e in errors:
                f.write(f"  - {e}\n")
        else:
            f.write("✅ Validation PASSED!\n")
    print("Done. Saved to test_results.txt")

if __name__ == "__main__":
    test_chunk()
