"""
Test to validate LLM JSON responses from Gemini 2.5 Pro
This script checks if the malformed JSON errors are due to:
1. Actual malformed JSON from the LLM
2. Truncated responses
3. Parsing issues in our code
"""

import json
import sys
from pathlib import Path

def test_json_validity(file_path):
    """Read a debug file and test if it contains valid JSON."""
    print(f"\n{'='*70}")
    print(f"Testing: {file_path.name}")
    print('='*70)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"File size: {len(content)} characters")
    print(f"First 200 chars: {content[:200]}")
    print(f"Last 200 chars: {content[-200:]}")
    
    # Check if it's wrapped in ```json``` markdown
    if content.strip().startswith('```json'):
        print("\n⚠️  Response is wrapped in markdown code block")
        # Extract JSON from markdown
        lines = content.strip().split('\n')
        json_lines = []
        in_json = False
        for line in lines:
            if line.strip() == '```json':
                in_json = True
                continue
            elif line.strip() == '```':
                in_json = False
                break
            elif in_json:
                json_lines.append(line)
        
        json_content = '\n'.join(json_lines)
        print(f"Extracted JSON size: {len(json_content)} characters")
    else:
        json_content = content
    
    # Try to parse the JSON
    try:
        parsed = json.loads(json_content)
        print("\n✅ JSON is VALID")
        print(f"Top-level keys: {list(parsed.keys())}")
        if 'sections' in parsed:
            print(f"Number of sections: {len(parsed.get('sections', []))}")
        return True, parsed
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON is MALFORMED")
        print(f"Error: {e}")
        print(f"Error at line {e.lineno}, column {e.colno}")
        
        # Show context around error
        lines = json_content.split('\n')
        if e.lineno <= len(lines):
            start = max(0, e.lineno - 3)
            end = min(len(lines), e.lineno + 2)
            print("\nContext around error:")
            for i in range(start, end):
                marker = " >>> " if i == e.lineno - 1 else "     "
                print(f"{marker}Line {i+1}: {lines[i]}")
        
        return False, None

def main():
    # Test the debug files from job 352c390d (downloaded locally)
    current_dir = Path(".")
    
    debug_files = [
        "debug_llm_chunk_0_attempt_0.txt",
        "debug_llm_chunk_0_attempt_1.txt",
        "debug_llm_chunk_1_attempt_0.txt",
        "debug_llm_chunk_1_attempt_1.txt",
        "debug_llm_chunk_1_attempt_2.txt",
    ]
    
    results = {}
    for filename in debug_files:
        file_path = current_dir / filename
        if file_path.exists():
            valid, parsed = test_json_validity(file_path)
            results[filename] = valid
        else:
            print(f"\n⚠️  File not found: {filename}")
            results[filename] = None
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print('='*70)
    for filename, valid in results.items():
        if valid is None:
            status = "NOT FOUND"
        elif valid:
            status = "✅ VALID"
        else:
            status = "❌ MALFORMED"
        print(f"{filename}: {status}")
    
    # Conclusion
    malformed_count = sum(1 for v in results.values() if v is False)
    valid_count = sum(1 for v in results.values() if v is True)
    
    print(f"\nMalformed: {malformed_count}, Valid: {valid_count}")
    
    if malformed_count > 0:
        print("\n🔍 DIAGNOSIS: Gemini 2.5 Pro IS returning malformed/truncated JSON")
        print("The retry mechanism is working as intended - it catches these errors and retries.")
    else:
        print("\n✅ All responses are valid JSON. The error might be in the parsing logic.")

if __name__ == "__main__":
    main()
