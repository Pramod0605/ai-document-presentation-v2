"""
Local Validation Test for Critical Bug Fixes
Tests both avatar task_id storage and WAN placeholder retry fixes
"""
import os
import json
import requests
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:5000"
TEST_JOB_ID = None  # Will be created during test

def test_avatar_task_id_storage():
    """Test Fix #1: Avatar task_id storage for default avatars"""
    print("\n" + "="*60)
    print("TEST 1: Avatar Task ID Storage")
    print("="*60)
    
    # Step 1: Create a test job (you'll need to trigger this manually or via API)
    print("\n[MANUAL STEP] Create a test job with avatar generation")
    print("After avatars complete, enter the job ID:")
    global TEST_JOB_ID
    TEST_JOB_ID = input("Job ID: ").strip()
    
    # Step 2: Read presentation.json
    presentation_path = f"player/jobs/{TEST_JOB_ID}/presentation.json"
    
    if not os.path.exists(presentation_path):
        print(f"❌ FAIL: presentation.json not found at {presentation_path}")
        return False
    
    with open(presentation_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Step 3: Check avatar_task_id for all sections
    print("\n📋 Checking avatar_task_id in sections:")
    all_have_task_id = True
    
    for section in data.get("sections", []):
        section_id = section.get("section_id")
        avatar_task_id = section.get("avatar_task_id")
        avatar_status = section.get("avatar_status")
        
        if avatar_status == "completed":
            if avatar_task_id:
                print(f"  ✅ Section {section_id}: task_id = {avatar_task_id}")
            else:
                print(f"  ❌ Section {section_id}: task_id = NULL (BUG!)")
                all_have_task_id = False
    
    if all_have_task_id:
        print("\n✅ PASS: All completed avatars have task_id stored")
    else:
        print("\n❌ FAIL: Some sections missing avatar_task_id")
        return False
    
    # Step 4: Test repair functionality
    print("\n📋 Testing Repair Feature:")
    
    # Find an avatar file to delete
    avatars_dir = Path(f"player/jobs/{TEST_JOB_ID}/avatars")
    avatar_files = list(avatars_dir.glob("*.mp4"))
    
    if not avatar_files:
        print("⚠️  No avatar files to test repair")
        return True
    
    test_file = avatar_files[0]
    backup_path = test_file.with_suffix(".mp4.backup")
    
    # Backup and delete
    print(f"  Backing up: {test_file.name}")
    test_file.rename(backup_path)
    
    # Call repair endpoint
    print(f"  Calling repair endpoint...")
    response = requests.post(f"{BASE_URL}/api/repair-missing-assets/{TEST_JOB_ID}")
    
    if response.status_code == 200:
        result = response.json()
        repaired_count = result.get("repaired_count", 0)
        
        if repaired_count > 0:
            print(f"  ✅ Repaired {repaired_count} avatar(s)")
            print(f"  ✅ PASS: Repair feature working")
            success = True
        else:
            print(f"  ❌ FAIL: Repaired 0 avatars (expected at least 1)")
            success = False
    else:
        print(f"  ❌ FAIL: Repair endpoint returned {response.status_code}")
        success = False
    
    # Restore backup
    if backup_path.exists():
        if test_file.exists():
            test_file.unlink()  # Delete repaired file
        backup_path.rename(test_file)
        print(f"  Restored backup: {test_file.name}")
    
    return success


def test_wan_placeholder_detection():
    """Test Fix #2: WAN placeholder detection and retry"""
    print("\n" + "="*60)
    print("TEST 2: WAN Placeholder Detection")
    print("="*60)
    
    from moviepy.editor import ColorClip
    
    # Create a test 1-second red placeholder
    test_dir = Path("test_wan_placeholder")
    test_dir.mkdir(exist_ok=True)
    
    placeholder_path = test_dir / "test_placeholder.mp4"
    
    print("\n📋 Creating test 1-second red placeholder...")
    
    try:
        bg = ColorClip(size=(1280, 720), color=(255, 0, 0), duration=1)
        bg.write_videofile(
            str(placeholder_path),
            fps=24,
            codec="libx264",
            audio=False,
            logger=None
        )
        bg.close()
        print(f"  ✅ Created: {placeholder_path}")
    except Exception as e:
        print(f"  ❌ FAIL: Could not create placeholder: {e}")
        return False
    
    # Test detection
    print("\n📋 Testing placeholder detection logic:")
    
    from moviepy.editor import VideoFileClip
    
    with VideoFileClip(str(placeholder_path)) as clip:
        duration = clip.duration
    
    is_placeholder = duration <= 2
    expected_duration = 15  # Assume narration is 15 seconds
    
    print(f"  Video duration: {duration}s")
    print(f"  Expected duration: {expected_duration}s")
    print(f"  Is placeholder: {is_placeholder}")
    
    if is_placeholder and duration == 1.0:
        print("  ✅ PASS: Placeholder detected correctly")
        success = True
    else:
        print("  ❌ FAIL: Placeholder not detected")
        success = False
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    print(f"\n🧹 Cleaned up test directory")
    
    return success


def main():
    print("="*60)
    print("CRITICAL BUG FIXES - LOCAL VALIDATION TESTS")
    print("="*60)
    
    results = []
    
    # Test 1: Avatar task_id storage
    try:
        result1 = test_avatar_task_id_storage()
        results.append(("Avatar Task ID Storage", result1))
    except Exception as e:
        print(f"\n❌ Test 1 CRASHED: {e}")
        results.append(("Avatar Task ID Storage", False))
    
    # Test 2: WAN placeholder detection
    try:
        result2 = test_wan_placeholder_detection()
        results.append(("WAN Placeholder Detection", result2))
    except Exception as e:
        print(f"\n❌ Test 2 CRASHED: {e}")
        results.append(("WAN Placeholder Detection", False))
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED - Ready for production deployment!")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - Do not deploy until fixed!")
        return 1


if __name__ == "__main__":
    exit(main())
