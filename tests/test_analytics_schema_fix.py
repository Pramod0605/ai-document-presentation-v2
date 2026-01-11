import json
import os
from pathlib import Path
from core.analytics import AnalyticsTracker
from core.renderer_executor import _update_analytics_safely

def test_analytics_schema_fix():
    print("Testing Analytics Schema Fix...")
    
    # 1. Create a dummy analytics.json
    dummy_path = Path("tests/dummy_analytics.json")
    if dummy_path.exists():
        os.remove(dummy_path)
        
    initial_data = {
        "job_id": "test_job",
        "pipeline_version": "1.5",
        "renderer": {
            "manim_videos": 0,
            "wan_videos": 0,
            "section_renders": []
        }
    }
    
    with open(dummy_path, "w") as f:
        json.dump(initial_data, f)
        
    # 2. Simulate WAN Background Update (using the fixed helper)
    result = {
        "status": "success",
        "duration_seconds": 12.5,
        "section_type": "content"
    }
    
    print(f"Calling _update_analytics_safely for section 'sec_1'...")
    _update_analytics_safely(dummy_path, "sec_1", result)
    
    # Debug: Print file content
    with open(dummy_path, "r") as f:
        print(f"DEBUG JSON CONTENT:\n{f.read()}\n")

    # Debug: Check introspection
    from core.analytics import RendererMetrics
    print(f"DEBUG: hasattr(RendererMetrics, 'section_renders') = {hasattr(RendererMetrics, 'section_renders')}")
    print(f"DEBUG: RendererMetrics fields: {RendererMetrics.__annotations__.keys()}")

    # 3. Load using AnalyticsTracker (The Real Test)
    print("Loading with AnalyticsTracker...")
    tracker = AnalyticsTracker("test_job")
    success = tracker.load_from_file(str(dummy_path))
    
    if not success:
        print("FAIL: AnalyticsTracker failed to load file.")
        return
        
    # 4. Assertions
    if tracker.analytics.renderer:
         renders = tracker.analytics.renderer.section_renders
         print(f"Loaded {len(renders)} section renders.")
    else:
         print("FAIL: tracker.analytics.renderer is None")
         renders = []
    
    if len(renders) == 1:
        r = renders[0]
        if r["section_id"] == "sec_1" and r["renderer"] == "wan" and r["status"] == "success":
            print("SUCCESS: Section render loaded correctly!")
        else:
            print(f"FAIL: Render data mismatch: {r}")
    else:
        print("FAIL: Expected 1 render detail.")
        
    # Cleanup
    # if dummy_path.exists():
    #    os.remove(dummy_path)

if __name__ == "__main__":
    test_analytics_schema_fix()
