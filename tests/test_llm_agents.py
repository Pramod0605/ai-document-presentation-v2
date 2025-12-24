"""
TEST-001: LLM Agent Validation Tests
Tests each V1.5 agent in isolation to verify output structure and constraints.

Usage:
    python tests/test_llm_agents.py [agent_name]
    
    agent_name: section_planner, narration_writer, visual_spec_artist, 
                renderer_spec, memory_agent, recap_agent, manim_code_generator
    
    If no agent_name provided, runs all tests.
"""

import os
import sys
import json
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agents.section_planner import SectionPlannerAgent
from core.agents.narration_writer import NarrationWriterAgent
from core.agents.visual_spec_artist import VisualSpecArtistAgent
from core.agents.renderer_spec_agent import RendererSpecAgent
from core.agents.memory_agent import MemoryFlashcardAgent
from core.agents.recap_agent import RecapSceneAgent
from core.agents.manim_code_generator import ManimCodeGenerator, build_manim_section_data


class TestColors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_result(test_name: str, passed: bool, message: str = ""):
    color = TestColors.GREEN if passed else TestColors.RED
    status = "PASS" if passed else "FAIL"
    print(f"{color}[{status}]{TestColors.RESET} {test_name}")
    if message:
        print(f"       {message}")


SAMPLE_CHUNK = {
    "chunk_id": "test_001",
    "title": "Introduction to Derivatives",
    "content": """The derivative of a function measures the rate at which the function's value changes.
    
For a function f(x), the derivative f'(x) is defined as:
f'(x) = lim(h→0) [f(x+h) - f(x)] / h

This limit, when it exists, gives us the instantaneous rate of change at any point x.

Example: For f(x) = x², the derivative is f'(x) = 2x.
This means at x=3, the function is changing at a rate of 6 units per unit change in x.""",
    "page_numbers": [1, 2],
    "order": 1
}


def test_section_planner():
    """TEST-001a: Section Planner output validation"""
    print(f"\n{TestColors.BLUE}=== Testing SectionPlanner ==={TestColors.RESET}")
    
    try:
        planner = SectionPlannerAgent()
        result = planner.plan([SAMPLE_CHUNK], "test_job")
        
        print_result("Returns list", isinstance(result, list), f"Got: {type(result)}")
        
        if not result:
            print_result("Has sections", False, "Empty result")
            return False
        
        has_intro = any(s.get("section_type") == "intro" for s in result)
        print_result("Has intro section", has_intro)
        
        has_summary = any(s.get("section_type") == "summary" for s in result)
        print_result("Has summary section", has_summary)
        
        all_valid = True
        for section in result:
            section_type = section.get("section_type")
            renderer = section.get("renderer")
            
            if renderer and renderer not in ["manim", "video", "none", None]:
                print_result(f"Section {section_type} renderer valid", False, f"Invalid renderer: {renderer}")
                all_valid = False
            
            if "avatar_width_percent" in section:
                width = section["avatar_width_percent"]
                if width not in [35, 45, 60]:
                    print_result(f"Section {section_type} avatar_width_percent", False, f"Invalid: {width}")
                    all_valid = False
        
        print_result("All sections have valid renderers", all_valid)
        
        no_hidden = True
        for section in result:
            if section.get("avatar_position") == "hidden":
                no_hidden = False
                break
        print_result("No hidden avatar positions (REQ-021)", no_hidden)
        
        return True
        
    except Exception as e:
        print_result("SectionPlanner execution", False, str(e))
        traceback.print_exc()
        return False


def test_narration_writer():
    """TEST-001b: Narration Writer output validation"""
    print(f"\n{TestColors.BLUE}=== Testing NarrationWriter ==={TestColors.RESET}")
    
    sample_section_plan = {
        "section_id": "sec_001",
        "section_type": "content",
        "title": "Understanding Derivatives",
        "teaching_objective": "Explain the concept of derivatives",
        "duration_target_seconds": 60,
        "source_chunk_id": "test_001"
    }
    
    try:
        writer = NarrationWriterAgent()
        result = writer.write(sample_section_plan, SAMPLE_CHUNK["content"], "test_job")
        
        print_result("Returns dict", isinstance(result, dict))
        
        has_full_text = "narration" in result and "full_text" in result.get("narration", {})
        print_result("Has narration.full_text", has_full_text)
        
        has_segments = "segments" in result and isinstance(result.get("segments"), list)
        print_result("Has segments list", has_segments)
        
        if has_segments and result["segments"]:
            seg = result["segments"][0]
            has_required = all(k in seg for k in ["segment_id", "text"])
            print_result("Segments have required fields", has_required)
        
        return True
        
    except Exception as e:
        print_result("NarrationWriter execution", False, str(e))
        traceback.print_exc()
        return False


def test_visual_spec_artist():
    """TEST-001c: Visual Spec Artist output validation"""
    print(f"\n{TestColors.BLUE}=== Testing VisualSpecArtist ==={TestColors.RESET}")
    
    sample_narration = {
        "section_id": "sec_001",
        "narration": {"full_text": "The derivative measures rates of change."},
        "segments": [
            {"segment_id": "seg_001", "text": "The derivative measures rates of change.", "duration_seconds": 5.0}
        ]
    }
    
    sample_section_plan = {
        "section_id": "sec_001",
        "section_type": "content",
        "renderer": "manim",
        "title": "Understanding Derivatives"
    }
    
    try:
        artist = VisualSpecArtistAgent()
        result = artist.specify(sample_section_plan, sample_narration, "test_job")
        
        print_result("Returns dict", isinstance(result, dict))
        
        has_visual_beats = "visual_beats" in result
        print_result("Has visual_beats", has_visual_beats)
        
        has_segment_enrichments = "segment_enrichments" in result
        print_result("Has segment_enrichments", has_segment_enrichments)
        
        no_hide = True
        if "segment_enrichments" in result:
            for enrich in result["segment_enrichments"]:
                dd = enrich.get("display_directives", {})
                if dd.get("avatar_layer") == "hide":
                    no_hide = False
                    break
        print_result("No 'hide' in avatar_layer (REQ-022)", no_hide)
        
        return True
        
    except Exception as e:
        print_result("VisualSpecArtist execution", False, str(e))
        traceback.print_exc()
        return False


def test_renderer_spec():
    """TEST-001d: Renderer Spec Agent output validation"""
    print(f"\n{TestColors.BLUE}=== Testing RendererSpecAgent ==={TestColors.RESET}")
    
    sample_section = {
        "section_id": "sec_001",
        "section_type": "content",
        "renderer": "manim",
        "title": "Understanding Derivatives"
    }
    
    sample_visual = {
        "visual_beats": [
            {"beat_id": "beat_001", "description": "Show derivative formula", "sync_to_segment": "seg_001"}
        ],
        "segment_enrichments": [
            {"segment_id": "seg_001", "visual_content": {"formula": "f'(x) = 2x"}}
        ]
    }
    
    try:
        agent = RendererSpecAgent()
        result = agent.generate_spec(sample_section, sample_visual, "test_job")
        
        print_result("Returns dict", isinstance(result, dict))
        
        has_manim_spec = "manim_scene_spec" in result
        print_result("Has manim_scene_spec for manim renderer", has_manim_spec)
        
        return True
        
    except Exception as e:
        print_result("RendererSpecAgent execution", False, str(e))
        traceback.print_exc()
        return False


def test_memory_agent():
    """TEST-001e: Memory Agent output validation"""
    print(f"\n{TestColors.BLUE}=== Testing MemoryFlashcardAgent ==={TestColors.RESET}")
    
    sample_sections = [
        {
            "section_id": "sec_001",
            "section_type": "content",
            "title": "Understanding Derivatives",
            "narration": {"full_text": "Derivatives measure the rate of change of a function."}
        }
    ]
    
    try:
        agent = MemoryFlashcardAgent()
        result = agent.generate(sample_sections, "test_job")
        
        print_result("Returns dict", isinstance(result, dict))
        
        has_flashcards = "flashcards" in result and isinstance(result.get("flashcards"), list)
        print_result("Has flashcards list", has_flashcards)
        
        has_avatar_layout = "avatar_layout" in result
        print_result("Has avatar_layout (REQ-023)", has_avatar_layout)
        
        if has_avatar_layout:
            layout = result["avatar_layout"]
            valid_width = layout.get("width_percent") in [35, 45, 60]
            print_result("avatar_layout.width_percent valid", valid_width, f"Got: {layout.get('width_percent')}")
        
        return True
        
    except Exception as e:
        print_result("MemoryFlashcardAgent execution", False, str(e))
        traceback.print_exc()
        return False


def test_recap_agent():
    """TEST-001f: Recap Agent output validation"""
    print(f"\n{TestColors.BLUE}=== Testing RecapSceneAgent ==={TestColors.RESET}")
    
    sample_sections = [
        {
            "section_id": "sec_001",
            "section_type": "content",
            "title": "Understanding Derivatives",
            "narration": {"full_text": "Derivatives measure the rate of change of a function."}
        }
    ]
    
    try:
        agent = RecapSceneAgent()
        result = agent.generate(sample_sections, "test_job")
        
        print_result("Returns dict", isinstance(result, dict))
        
        has_prompts = "video_prompts" in result and isinstance(result.get("video_prompts"), list)
        print_result("Has video_prompts list", has_prompts)
        
        has_avatar_layout = "avatar_layout" in result
        print_result("Has avatar_layout (REQ-024)", has_avatar_layout)
        
        if has_prompts and result["video_prompts"]:
            prompt = result["video_prompts"][0]
            has_required = all(k in prompt for k in ["prompt_id", "visual_prompt"])
            print_result("Video prompts have required fields", has_required)
        
        return True
        
    except Exception as e:
        print_result("RecapSceneAgent execution", False, str(e))
        traceback.print_exc()
        return False


def test_manim_code_generator():
    """TEST-001g: Manim Code Generator validation"""
    print(f"\n{TestColors.BLUE}=== Testing ManimCodeGenerator ==={TestColors.RESET}")
    
    sample_section = {
        "title": "Derivative Visualization",
        "section_type": "content"
    }
    
    sample_segments = [
        {"segment_id": "seg_001", "text": "Let's visualize the derivative.", "duration_seconds": 5.0},
        {"segment_id": "seg_002", "text": "The slope of the tangent line.", "duration_seconds": 4.0}
    ]
    
    sample_visual_beats = [
        {"beat_id": "beat_001", "description": "Show function curve", "sync_to_segment": "seg_001"},
        {"beat_id": "beat_002", "description": "Draw tangent line", "sync_to_segment": "seg_002"}
    ]
    
    sample_enrichments = [
        {"segment_id": "seg_001", "visual_content": {"formula": "f(x) = x^2", "labels": ["curve"]}},
        {"segment_id": "seg_002", "visual_content": {"formula": "f'(x) = 2x", "labels": ["tangent"]}}
    ]
    
    try:
        input_data = build_manim_section_data(
            sample_section, 
            sample_segments, 
            sample_visual_beats, 
            sample_enrichments
        )
        
        print_result("build_manim_section_data returns dict", isinstance(input_data, dict))
        
        has_title = "section_title" in input_data
        print_result("Has section_title", has_title)
        
        has_segments = "narration_segments" in input_data
        print_result("Has narration_segments", has_segments)
        
        if has_segments:
            seg = input_data["narration_segments"][0]
            uses_duration = "duration" in seg and "duration_seconds" not in seg
            print_result("Segments use 'duration' not 'duration_seconds'", uses_duration, f"Fields: {list(seg.keys())}")
            
            duration_is_float = isinstance(seg.get("duration"), float)
            print_result("Duration is float type", duration_is_float)
        
        generator = ManimCodeGenerator()
        print_result("ManimCodeGenerator instantiated", True)
        
        test_section_data = {"narration_segments": [{"duration": 5.0}]}
        validation_errors = generator.validate_code("self.play(Create(Circle()))", test_section_data)
        print_result("Validation function works", isinstance(validation_errors, list))
        
        bad_code = "placeholder = Dot()"
        errors = generator.validate_code(bad_code, test_section_data)
        catches_placeholder = any("placeholder" in e.lower() or "dot()" in e.lower() for e in errors)
        print_result("Catches Dot() placeholder pattern", catches_placeholder, f"Errors: {errors}")
        
        return True
        
    except Exception as e:
        print_result("ManimCodeGenerator execution", False, str(e))
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all agent tests"""
    print(f"\n{TestColors.BLUE}{'='*60}")
    print("TEST-001: LLM Agent Validation Suite")
    print(f"{'='*60}{TestColors.RESET}")
    
    results = {}
    
    results["section_planner"] = test_section_planner()
    results["narration_writer"] = test_narration_writer()
    results["visual_spec_artist"] = test_visual_spec_artist()
    results["renderer_spec"] = test_renderer_spec()
    results["memory_agent"] = test_memory_agent()
    results["recap_agent"] = test_recap_agent()
    results["manim_code_generator"] = test_manim_code_generator()
    
    print(f"\n{TestColors.BLUE}{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}{TestColors.RESET}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        color = TestColors.GREEN if result else TestColors.RED
        status = "PASS" if result else "FAIL"
        print(f"  {color}[{status}]{TestColors.RESET} {test}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    return all(results.values())


if __name__ == "__main__":
    if len(sys.argv) > 1:
        agent = sys.argv[1].lower()
        test_map = {
            "section_planner": test_section_planner,
            "narration_writer": test_narration_writer,
            "visual_spec_artist": test_visual_spec_artist,
            "renderer_spec": test_renderer_spec,
            "memory_agent": test_memory_agent,
            "recap_agent": test_recap_agent,
            "manim_code_generator": test_manim_code_generator
        }
        if agent in test_map:
            test_map[agent]()
        else:
            print(f"Unknown agent: {agent}")
            print(f"Available: {', '.join(test_map.keys())}")
    else:
        run_all_tests()
