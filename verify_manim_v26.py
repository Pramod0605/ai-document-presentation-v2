import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation")
sys.path.append(str(project_root))

from render.manim.manim_runner import render_manim_video

def verify_sync_routing():
    print("=" * 60)
    print("VERIFYING MANIM V2.6 ROUTING")
    print("=" * 60)
    
    # Load test job
    pres_path = project_root / "debug" / "job123456" / "presentation.json"
    with open(pres_path, "r", encoding="utf-8") as f:
        pres = json.load(f)
    
    # Section 3 is Manim with segment_specs
    topic = pres["sections"][2] # 0-indexed, so 2 is section 3
    topic["id"] = 3
    topic_id = 3
    
    print(f"✓ Loaded Section {topic_id}: {topic['title']}")
    
    # Prepare output dir
    output_dir = project_root / "debug" / "v26_test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run in DRY RUN mode to verify logic
    print(f"\n⏳ Running render_manim_video(dry_run=True)...")
    results = render_manim_video(
        topic=topic,
        output_dir=str(output_dir),
        dry_run=True
    )
    
    print(f"\n📊 Results:")
    print(f"  Count: {len(results)}")
    for i, path in enumerate(results):
        print(f"  [{i}] {path}")
    
    # Verify beat_videos population on segments
    print(f"\n🔍 Verifying segment-level beat_videos:")
    segments = topic.get("narration", {}).get("segments", [])
    manim_found = 0
    for seg in segments:
        if seg.get("beat_videos"):
            print(f"  ✓ {seg['segment_id']}: {seg['beat_videos']}")
            manim_found += 1
    
    if manim_found == 6:
        print(f"\n✅ SUCCESS: All 6 Manim segments correctly linked.")
    else:
        print(f"\n❌ FAILURE: Expected 6 links, found {manim_found}.")
        return False

    # Check for name Aligned with WAN
    if "beat_0" in results[0]:
        print(f"✅ SUCCESS: Naming convention topic_3_beat_0.mp4 followed.")
    else:
        print(f"❌ FAILURE: Naming convention mismatch.")
        return False

    return True

if __name__ == "__main__":
    success = verify_sync_routing()
    sys.exit(0 if success else 1)
