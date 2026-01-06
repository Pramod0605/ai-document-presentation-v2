"""
Unit Test: Manim Spec Generation (Gemini 2.5 Pro)

Tests that the RendererSpecAgent can generate valid manim_scene_spec.
"""
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_manim_spec_generation():
    """Test Gemini 2.5 Pro spec generation for Manim."""
    from core.agents.renderer_spec_agent import RendererSpecAgent
    
    print("=" * 60)
    print("TEST: Manim Spec Generation (Gemini 2.5 Pro)")
    print("=" * 60)
    
    # Create agent
    agent = RendererSpecAgent(renderer_type="manim")
    print(f"✓ Agent created: {agent.name}")
    print(f"  Model: {agent.model}")
    print(f"  System prompt: {agent.system_prompt_file}")
    
    # Test input (minimal example)
    test_input = {
        "section_id": 1,
        "renderer": "manim",
        "visual_beats": [
            {
                "scene_setup": "Coordinate plane with a triangle",
                "objects_and_properties": "Triangle ABC with sides a, b, c",
                "motion_sequence": "Draw triangle, then label vertices",
                "labels_and_text": "Label A at top, B at bottom-right, C at bottom-left",
                "purpose": "Introduce triangle geometry",
                "duration_seconds": 10
            }
        ],
        "narration_summary": "We begin with a right triangle to explore the Pythagorean theorem."
    }
    
    print(f"\n✓ Test input prepared:")
    print(f"  Visual beats: {len(test_input['visual_beats'])}")
    print(f"  Narration: {test_input['narration_summary'][:50]}...")
    
    # Run agent
    try:
        print(f"\n⏳ Calling Gemini 2.5 Pro...")
        result = agent.run(**test_input)
        
        print(f"\n✅ Spec generated successfully!")
        print(f"  Section ID: {result.get('section_id')}")
        print(f"  Renderer: {result.get('renderer')}")
        
        spec = result.get("manim_scene_spec", {})
        print(f"\n📋 manim_scene_spec content:")
        print(f"  Objects: {len(spec.get('objects', []))}")
        print(f"  Forces: {len(spec.get('forces', []))}")
        print(f"  Equations: {len(spec.get('equations', []))}")
        print(f"  Animation sequence: {len(spec.get('animation_sequence', []))}")
        
        # Validate structure
        errors = []
        if not spec:
            errors.append("Missing manim_scene_spec")
        if not isinstance(spec.get("objects"), list):
            errors.append("objects is not a list")
        if not isinstance(spec.get("animation_sequence"), list):
            errors.append("animation_sequence is not a list")
        
        if errors:
            print(f"\n❌ VALIDATION ERRORS:")
            for err in errors:
                print(f"  - {err}")
            return False
        
        # Print full spec
        print(f"\n📄 Full spec (JSON):")
        print(json.dumps(spec, indent=2)[:500] + "...")
        
        print(f"\n✅ TEST PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_manim_spec_generation()
    sys.exit(0 if success else 1)
