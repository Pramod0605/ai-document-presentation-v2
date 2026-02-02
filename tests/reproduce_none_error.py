
import sys
import os
import unittest
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.unified_content_generator import extract_json_from_response, JSONParseError

class TestNoneErrorFix(unittest.TestCase):
    
    def test_extracted_json_none_input(self):
        """Test that passing None raises ValueError"""
        print("\nRunning test_extracted_json_none_input...")
        with self.assertRaises(ValueError) as cm:
            extract_json_from_response(None)
        print(f"Caught expected error: {cm.exception}")

    def test_extracted_json_malformed_input(self):
        """Test that malformed JSON raises JSONParseError, NOT None"""
        print("\nRunning test_extracted_json_malformed_input...")
        malformed = "{ 'broken': key_value, " 
        
        with self.assertRaises(JSONParseError) as cm:
            result = extract_json_from_response(malformed)
            # If result returned None, this line would be reached and strict check would fail
            if result is None:
                self.fail("extract_json_from_response returned None for malformed input! usage error.")
                
        print(f"Caught expected error: {cm.exception}")

    def test_valid_json(self):
        """Ensure valid JSON still works"""
        valid = '{"key": "value"}'
        result = extract_json_from_response(valid)
        self.assertEqual(result, {"key": "value"})
        print("\nValid JSON passed.")

if __name__ == '__main__':
    unittest.main()
