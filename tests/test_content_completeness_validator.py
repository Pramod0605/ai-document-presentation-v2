"""
Unit Tests for Content Completeness Validator

Tests validation logic for images, topics, key terms, and content volume.
"""

import unittest
import json
import os
import tempfile
import shutil
from pathlib import Path

from core.validators.content_completeness_validator import ContentCompletenessValidator, validate_content_completeness


class TestContentCompletenessValidator(unittest.TestCase):
    """Test cases for Content Completeness Validator"""
    
    def setUp(self):
        """Create temporary test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.validator = ContentCompletenessValidator(tolerance_percent=20.0)
        
    def tearDown(self):
        """Clean up temporary files"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_validation_passes_complete_content(self):
        """Test that validation passes when all content is present"""
        
        # Create test chunker output
        chunker_data = {
            "source_topic": "Biology Basics",
            "topics": [
                {
                    "topic_id": "topic_1",
                    "title": "Cell Structure",
                    "key_terms": ["mitochondria", "nucleus", "membrane"]
                },
                {
                    "topic_id": "topic_2",
                    "title": "Photosynthesis",
                    "key_terms": ["chloroplast", "glucose", "sunlight"]
                }
            ],
            "validation_metadata": {
                "total_topics": 2,
                "topic_ids": ["topic_1", "topic_2"],
                "topic_titles": ["Cell Structure", "Photosynthesis"],
                "all_key_terms": ["mitochondria", "nucleus", "membrane", "chloroplast", "glucose", "sunlight"],
                "source_word_count": 500,
                "total_images": 2
            }
        }
        
        # Create test presentation with ALL key terms in narration
        presentation = {
            "sections": [
                {
                    "topic_id": "topic_1",
                    "title": "Cell Structure",
                    "narration": {
                        "segments": [
                            {
                                # Include ALL key terms: mitochondria, nucleus, membrane
                                "text": "The cell contains mitochondria for energy production, a nucleus that controls activities, and a protective membrane.",
                                "visual_content": {
                                    "image_id": "cell_diagram.png"
                                }
                            }
                        ]
                    }
                },
                {
                    "topic_id": "topic_2",
                    "title": "Photosynthesis",
                    "narration": {
                        "segments": [
                            {
                                # Include ALL key terms: chloroplast, glucose, sunlight
                                "text": "Photosynthesis occurs in the chloroplast where sunlight energy is converted into glucose sugar.",
                                "visual_content": {
                                    "image_id": "photosynthesis.png"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        # Source markdown should have ~500 words to match chunker metadata
        # Create realistic content with actual key terms
        source_markdown = """
        # Cell Structure
        
        The cell is the basic unit of life. Inside the cell, we find several important organelles.
        The mitochondria are responsible for energy production. The nucleus controls all cellular
        activities and contains genetic material. The cell is surrounded by a protective membrane
        that regulates what enters and exits.
        
        # Photosynthesis
        
        Photosynthesis is the process by which plants make food. This process occurs in the
        chloroplast organelles. During photosynthesis, sunlight energy is captured and converted
        into glucose sugar molecules that the plant can use for energy.
        """ * 6  # Repeat to get ~500 words

        
        # Save chunker output
        artifacts_dir = Path(self.test_dir) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        chunker_path = artifacts_dir / "01_chunker.json"
        with open(chunker_path, "w") as f:
            json.dump(chunker_data, f)
        
        # Create image files
        images_dir = Path(self.test_dir) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "cell_diagram.png").touch()
        (images_dir / "photosynthesis.png").touch()
        
        # Run validation
        result = self.validator.validate(
            presentation=presentation,
            chunker_output_path=str(chunker_path),
            images_dir=str(images_dir),
            source_markdown=source_markdown
        )
        
        # Assert validation passed
        self.assertEqual(result["validation_status"], "passed")
        self.assertEqual(result["checks"]["image_coverage"]["status"], "passed")
        self.assertEqual(result["checks"]["topic_coverage"]["status"], "passed")
        self.assertEqual(result["checks"]["key_terms"]["status"], "passed")
        self.assertEqual(result["checks"]["content_volume"]["status"], "passed")
    
    def test_validation_fails_missing_image(self):
        """Test that validation fails when images are missing"""
        
        chunker_data = {
            "topics": [],
            "validation_metadata": {
                "total_topics": 0,
                "topic_ids": [],
                "all_key_terms": [],
                "source_word_count": 100,
                "total_images": 2
            }
        }
        
        presentation = {
            "sections": [
                {
                    "narration": {
                        "segments": [
                            {
                                "text": "test",
                                "visual_content": {
                                    "image_id": "diagram_1.png"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        # Save chunker
        artifacts_dir = Path(self.test_dir) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        with open(artifacts_dir / "01_chunker.json", "w") as f:
            json.dump(chunker_data, f)
        
        # Create images dir with 2 files but only 1 referenced
        images_dir = Path(self.test_dir) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "diagram_1.png").touch()
        (images_dir / "diagram_2.png").touch()  # This one is NOT referenced
        
        # Run validation
        result = self.validator.validate(
            presentation=presentation,
            chunker_output_path=str(artifacts_dir / "01_chunker.json"),
            images_dir=str(images_dir),
            source_markdown="test " * 25
        )
        
        # Should fail because diagram_2.png is not referenced
        self.assertEqual(result["validation_status"], "failed")
        self.assertEqual(result["checks"]["image_coverage"]["status"], "failed")
        self.assertIn("diagram_2.png", result["checks"]["image_coverage"]["missing_images"])
    
    def test_validation_fails_missing_topic(self):
        """Test that validation fails when topics are missing"""
        
        chunker_data = {
            "topics": [
                {"topic_id": "topic_1", "title": "Topic One", "key_terms": []},
                {"topic_id": "topic_2", "title": "Topic Two", "key_terms": []},
                {"topic_id": "topic_3", "title": "Topic Three", "key_terms": []}
            ],
            "validation_metadata": {
                "total_topics": 3,
                "topic_ids": ["topic_1", "topic_2", "topic_3"],
                "topic_titles": ["Topic One", "Topic Two", "Topic Three"],
                "all_key_terms": [],
                "source_word_count": 100,
                "total_images": 0
            }
        }
        
        # Presentation only has 2 topics - missing topic_3
        presentation = {
            "sections": [
                {
                    "topic_id": "topic_1",
                    "title": "Topic One",
                    "narration": {"segments": [{"text": "content"}]}
                },
                {
                    "topic_id": "topic_2",
                    "title": "Topic Two",
                    "narration": {"segments": [{"text": "content"}]}
                }
            ]
        }
        
        # Save chunker
        artifacts_dir = Path(self.test_dir) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        with open(artifacts_dir / "01_chunker.json", "w") as f:
            json.dump(chunker_data, f)
        
        images_dir = Path(self.test_dir) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # Run validation
        result = self.validator.validate(
            presentation=presentation,
            chunker_output_path=str(artifacts_dir / "01_chunker.json"),
            images_dir=str(images_dir),
            source_markdown="test " * 25
        )
        
        # Should fail
        self.assertEqual(result["validation_status"], "failed")
        self.assertEqual(result["checks"]["topic_coverage"]["status"], "failed")
        self.assertEqual(len(result["checks"]["topic_coverage"]["missing_topics"]), 1)
        self.assertEqual(result["checks"]["topic_coverage"]["missing_topics"][0]["topic_id"], "topic_3")
    
    def test_retry_prompt_generation(self):
        """Test that retry prompt is generated correctly"""
        
        chunker_data = {
            "topics": [
                {"topic_id": "topic_1", "title": "Missing Topic", "key_terms": ["term1", "term2"]}
            ],
            "validation_metadata": {
                "total_topics": 1,
                "topic_ids": ["topic_1"],
                "topic_titles": ["Missing Topic"],
                "all_key_terms": ["term1", "term2"],
                "source_word_count": 500,
                "total_images": 1
            }
        }
        
        # Empty presentation - everything missing
        presentation = {
            "sections": []
        }
        
        # Save chunker
        artifacts_dir = Path(self.test_dir) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        with open(artifacts_dir / "01_chunker.json", "w") as f:
            json.dump(chunker_data, f)
        
        # Create images
        images_dir = Path(self.test_dir) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "test_image.png").touch()
        
        # Run validation
        result = self.validator.validate(
            presentation=presentation,
            chunker_output_path=str(artifacts_dir / "01_chunker.json"),
            images_dir=str(images_dir),
            source_markdown="test " * 125
        )
        
        # Check retry prompt
        self.assertEqual(result["validation_status"], "failed")
        self.assertIn("retry_prompt_enhancement", result)
        retry_prompt = result["retry_prompt_enhancement"]
        
        # Verify prompt contains missing information
        self.assertIn("MISSING IMAGE REFERENCES", retry_prompt)
        self.assertIn("test_image.png", retry_prompt)
        self.assertIn("MISSING TOPICS", retry_prompt)
        self.assertIn("Missing Topic", retry_prompt)
        self.assertIn("MISSING KEY TERMS", retry_prompt)


if __name__ == "__main__":
    unittest.main()
