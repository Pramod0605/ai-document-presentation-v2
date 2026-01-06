"""
Script to test V2.5 Director Pipeline with MOCK LLM.
Proves that the pipeline handles Director Schema and Pointers correctly.
"""

import os
import sys
import logging
import json
from pathlib import Path
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline_unified import process_markdown_unified

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MOCK_RESPONSE = {
  "presentation_title": "Cell Biology: Structure and Function",
  "sections": [
    {
      "section_id": "s1",
      "section_type": "intro",
      "title": "Introduction",
      "narration": {
        "segments": [{
           "segment_id": "seg_0",
           "text": "Welcome to this lesson on Cell Biology.",
           "display_directives": {"text_layer": "hide", "avatar_layer": "show", "visual_layer": "hide"}
        }]
      }
    },
    {
      "section_id": "s2",
      "section_type": "content",
      "title": "The Cell Membrane",
      "narration": {
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "The cell membrane determines what enters and leaves the cell.",
            "display_directives": {"text_layer": "show", "visual_layer": "hide"},
            "visual_content": {
              "visual_type": "text",
              "markdown_pointer": {
                "start_phrase": "The cell membrane, also known",
                "end_phrase": "what enters and exits the cell."
              }
            }
          }
        ]
      }
    }
  ]
}

def mock_llm_call(*args, **kwargs):
    logger.info("⚡ [MOCK] Intercepted LLM Call. Returning Mock V2.5 JSON.")
    return json.dumps(MOCK_RESPONSE), {"input_tokens": 100, "output_tokens": 100}

def test_pipeline():
    # Input file matches the pointers in MOCK_RESPONSE
    input_file = Path("test_inputs/test_biology_cells.md")
    
    # Test Job ID
    job_id = "test_director_v25_mock"
    output_dir = Path(f"player/jobs/{job_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_file.exists():
        logger.error("Input file missing")
        return

    markdown_content = input_file.read_text(encoding="utf-8")
    
    logger.info(f"Starting V2.5 Director Pipeline MOCK Test for Job: {job_id}")

    # Patch the LLM call where it is defined/imported in unified_director_generator
    with patch('core.unified_director_generator.call_openrouter_llm', side_effect=mock_llm_call):
        try:
            presentation, tracker = process_markdown_unified(
                markdown_content=markdown_content,
                subject="Biology",
                grade="Grade 10",
                job_id=job_id,
                output_dir=output_dir,
                pipeline_version="v15_v2_director",
                dry_run=True,
                skip_wan=True
            )
            
            logger.info("✅ Pipeline Success (Mocked)!")
            
            # Save output
            pres_path = output_dir / "presentation.json"
            with open(pres_path, "w", encoding="utf-8") as f:
                json.dump(presentation, f, indent=2)
                
            logger.info(f"Verified Pointers:")
            sections = presentation.get("sections", [])
            found_pointer = False
            for sec in sections:
                segments = sec.get("narration", {}).get("segments", [])
                for seg in segments:
                    pointer = seg.get("visual_content", {}).get("markdown_pointer")
                    if pointer:
                        found_pointer = True
                        logger.info(f"   MATCH! Pointer found: {pointer}")
            
            if not found_pointer:
                logger.error("❌ No pointers found in output!")
            else:
                logger.info("✅ Pointer Verification Passed")

        except Exception as e:
            logger.error(f"❌ Pipeline Failed: {e}", exc_info=True)

if __name__ == "__main__":
    test_pipeline()
