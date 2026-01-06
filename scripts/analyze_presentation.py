import json
import os
import sys

JOB_ID = "f3434c3c"
JSON_PATH = f"player/jobs/{JOB_ID}/presentation.json"

if not os.path.exists(JSON_PATH):
    print(f"❌ File not found: {JSON_PATH}")
    sys.exit(1)

try:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    sections = data.get("sections", [])
    
    counts = {
        "intro": 0,
        "summary": 0,
        "memory": 0,
        "recap": 0,
        "content_slide": 0,
        "quiz": 0,
        "other": 0
    }
    
    print(f"📄 Analyzing {len(sections)} sections for Job {JOB_ID}...\n")
    
    for i, sec in enumerate(sections):
        stype = sec.get("section_type", sec.get("type", "unknown"))
        
        # Normalize type for counting
        if stype in counts:
            counts[stype] += 1
        else:
            counts["other"] += 1
            print(f"⚠️ Unknown Type: {stype} (Index {i})")

    # Print Report
    print("--- SECTION BREAKDOWN ---")
    print(f"🔹 Intro:    {counts['intro']} (Expected: 1)")
    print(f"🔹 Summary:  {counts['summary']} (Expected: 1)")
    print(f"🔹 Memory:   {counts['memory']} (Expected: 1)")
    print(f"🔹 Recap:    {counts['recap']} (Expected: 1)")
    print(f"🔸 Content:  {counts['content_slide']}")
    print(f"🔸 Quiz:     {counts['quiz']}")
    print("------------------------")
    
    total_expected = counts['intro'] + counts['summary'] + counts['memory'] + counts['recap'] + counts['content_slide'] + counts['quiz']
    if total_expected == len(sections):
        print("✅ All sections accounted for.")
    else:
        print(f"❌ Mismatch! Total sections: {len(sections)}, Counted: {total_expected}")

except Exception as e:
    print(f"❌ Error reading JSON: {e}")
