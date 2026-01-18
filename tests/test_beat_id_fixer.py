
import pytest
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from utilities.fix_wan_beat_ids import fix_beat_ids

def test_fix_wan_beat_ids():
    # Mock presentation
    presentation = {
        "sections": [
            {
                "section_id": 1,
                "renderer": "none",
                "section_type": "intro",
                "video_prompts": [{"beat_id": "topic_section_1_seg_1_beat_1"}]
            },
            {
                "section_id": 12,
                "renderer": "video",
                "section_type": "content",
                "video_prompts": [
                    {"beat_id": "topic_section_1_seg_12_beat_1"},
                    {"beat_id": "topic_section_1_seg_13_beat_1"}
                ],
                "narration": {
                    "segments": [
                        {"segment_id": "seg_12", "beat_videos": ["topic_section_1_seg_12_beat_1"]},
                        {"segment_id": "seg_13", "beat_videos": ["topic_section_1_seg_13_beat_1"]}
                    ]
                }
            }
        ]
    }
    
    fixed = fix_beat_ids(presentation)
    
    # Assertions
    assert fixed == 4 # 2 prompts + 2 narration beats
    
    # Section 1 should NOT be changed
    assert presentation["sections"][0]["video_prompts"][0]["beat_id"] == "topic_section_1_seg_1_beat_1"
    
    # Section 12 SHOULD be changed
    assert presentation["sections"][1]["video_prompts"][0]["beat_id"] == "topic_section_12_seg_12_beat_1"
    assert presentation["sections"][1]["narration"]["segments"][0]["beat_videos"][0] == "topic_section_12_seg_12_beat_1"

def test_fix_already_correct():
    presentation = {
        "sections": [
            {
                "section_id": 3,
                "renderer": "video",
                "video_prompts": [{"beat_id": "topic_section_3_seg_1_beat_1"}]
            }
        ]
    }
    fixed = fix_beat_ids(presentation)
    assert fixed == 0
    assert presentation["sections"][0]["video_prompts"][0]["beat_id"] == "topic_section_3_seg_1_beat_1"
