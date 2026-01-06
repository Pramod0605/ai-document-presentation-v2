import sys
import os
import json
import time

# Force Key
os.environ["DATALAB_API_KEY"] = "WmFbeYfN6tUoCNfHoGi4Xy66W5WqOud3Kr1FXmHYmW0"

# Add root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.datalab_client import document_to_markdown

PDF_PATH = r"C:\Users\email\Downloads\sslc ch 5 arithmatic progression.pdf"

print("--- DATALAB CONNECTION TEST ---")
print(f"Target: {PDF_PATH}")
print(f"Key: {os.environ['DATALAB_API_KEY'][:5]}...")

try:
    start = time.time()
    result = document_to_markdown(PDF_PATH)
    duration = time.time() - start
    
    print("\n✅ SUCCESS: Datalab Conversion Complete")
    print(f"⏱️ Time: {duration:.2f}s")
    print(f"📄 Pages: {result.page_count}")
    print(f"📝 Markdown Length: {len(result.markdown)} chars")
    print(f"🖼️ Images Found: {len(result.images)}")
    
    # Save the 'JSON' the user asked about (The full conversion result structure)
    debug_dump = {
        "page_count": result.page_count,
        "metadata": result.metadata,
        "markdown_preview": result.markdown[:500] + "...",
        "image_count": len(result.images)
    }
    
    with open("datalab_verify_result.json", "w") as f:
        json.dump(debug_dump, f, indent=2)
        print("\nSaved result to: datalab_verify_result.json")

except Exception as e:
    print(f"\n❌ FAILURE: {e}")
