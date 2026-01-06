"""
Test Pointer Resolution Logic
Verifies that text can be accurately extracted from markdown using start/end phrases.
"""

import unittest

class TestPointerResolution(unittest.TestCase):
    
    def setUp(self):
        self.source_markdown = """
# Biology: The Living World

All living organisms share certain characteristics that distinguish them from non-living things.
Growth is one of the most fundamental characteristics. All living organisms grow.
Increase in mass and increase in number of individuals are twin characteristics of growth.

In plants, this growth by cell division occurs continuously throughout their life span.
In animals, this growth is seen only up to a certain age. However, cell division occurs
in certain tissues to replace lost cells.

Metabolism is another defining feature. All living organisms are made of chemicals.
"""
    
    def resolve_pointer(self, markdown, start_phrase, end_phrase):
        """Python implementation of the Player V2.5 resolution logic"""
        if not start_phrase or not end_phrase:
            return None
            
        start_idx = markdown.find(start_phrase)
        if start_idx == -1:
            return None
            
        # Search for end phrase AFTER the start phrase
        end_idx = markdown.find(end_phrase, start_idx)
        if end_idx == -1:
            return None
            
        # Extract content inclusive of end_phrase
        return markdown[start_idx : end_idx + len(end_phrase)]

    def test_single_sentence(self):
        start = "All living organisms grow."
        end = "grow."
        result = self.resolve_pointer(self.source_markdown, start, end)
        self.assertEqual(result, "All living organisms grow.")

    def test_multi_sentence_paragraph(self):
        start = "In plants, this growth"
        end = "replace lost cells."
        
        expected = """In plants, this growth by cell division occurs continuously throughout their life span.
In animals, this growth is seen only up to a certain age. However, cell division occurs
in certain tissues to replace lost cells."""
        
        result = self.resolve_pointer(self.source_markdown, start, end)
        self.assertEqual(result, expected)

    def test_missing_start_phrase(self):
        result = self.resolve_pointer(self.source_markdown, "Non-existent phrase", "grow.")
        self.assertIsNone(result)

    def test_missing_end_phrase(self):
        result = self.resolve_pointer(self.source_markdown, "All living organisms", "Non-existent end")
        self.assertIsNone(result)

    def test_end_before_start(self):
        # "Metabolism" appears later, "Biology" appears earlier
        result = self.resolve_pointer(self.source_markdown, "Metabolism", "Biology")
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
