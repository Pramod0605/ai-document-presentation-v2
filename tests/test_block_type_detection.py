"""
Unit tests for ISS-160 block_type detection in SmartChunker.
"""
import pytest
from core.smart_chunker import detect_block_type, has_inline_latex, parse_content_blocks


class TestDetectBlockType:
    """Test block_type detection from markdown lines."""
    
    def test_paragraph(self):
        assert detect_block_type("This is a regular paragraph.") == "paragraph"
        assert detect_block_type("  Indented text  ") == "paragraph"
    
    def test_heading_as_paragraph(self):
        assert detect_block_type("# Heading 1") == "paragraph"
        assert detect_block_type("## Heading 2") == "paragraph"
        assert detect_block_type("### Heading 3") == "paragraph"
    
    def test_unordered_list(self):
        assert detect_block_type("- Item one") == "unordered_list"
        assert detect_block_type("* Item two") == "unordered_list"
        assert detect_block_type("+ Item three") == "unordered_list"
        assert detect_block_type("  - Nested item") == "unordered_list"
    
    def test_ordered_list(self):
        assert detect_block_type("1. First step") == "ordered_list"
        assert detect_block_type("2. Second step") == "ordered_list"
        assert detect_block_type("10. Tenth item") == "ordered_list"
        assert detect_block_type("  3. Indented step") == "ordered_list"
    
    def test_formula_block(self):
        assert detect_block_type("$$\\int_0^1 f(x) dx$$") == "formula"
        assert detect_block_type("The formula is $x^2$") == "formula"
    
    def test_blockquote(self):
        assert detect_block_type("> This is a quote") == "blockquote"
        assert detect_block_type(">Tight quote") == "blockquote"
    
    def test_empty_line(self):
        assert detect_block_type("") == "paragraph"
        assert detect_block_type("   ") == "paragraph"


class TestHasInlineLatex:
    """Test inline LaTeX detection."""
    
    def test_has_inline(self):
        assert has_inline_latex("The ratio $\\sin\\theta$ is defined as") == True
        assert has_inline_latex("Multiple $a$ and $b$ formulas") == True
    
    def test_no_inline(self):
        assert has_inline_latex("Regular text without formulas") == False
        assert has_inline_latex("Price is $50 for the book") == False  # Not LaTeX
    
    def test_block_latex_not_inline(self):
        assert has_inline_latex("$$\\int f(x)$$") == False


class TestParseContentBlocks:
    """Test full content block parsing."""
    
    def test_single_paragraph(self):
        md = "This is a simple paragraph."
        blocks = parse_content_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["block_type"] == "paragraph"
        assert blocks[0]["verbatim_content"] == "This is a simple paragraph."
    
    def test_multiple_paragraphs(self):
        md = """First paragraph.

Second paragraph."""
        blocks = parse_content_blocks(md)
        assert len(blocks) == 2
        assert blocks[0]["block_type"] == "paragraph"
        assert blocks[1]["block_type"] == "paragraph"
    
    def test_bullet_list(self):
        md = """- Item 1
- Item 2
- Item 3"""
        blocks = parse_content_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["block_type"] == "unordered_list"
        assert blocks[0]["items"] == ["Item 1", "Item 2", "Item 3"]
    
    def test_ordered_list(self):
        md = """1. First step
2. Second step
3. Third step"""
        blocks = parse_content_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["block_type"] == "ordered_list"
        assert blocks[0]["items"] == ["First step", "Second step", "Third step"]
    
    def test_mixed_content(self):
        md = """# Introduction

This is a paragraph with $\\sin\\theta$ formula.

- Bullet point 1
- Bullet point 2

1. Step one
2. Step two"""
        blocks = parse_content_blocks(md)
        assert len(blocks) >= 3
        
        types = [b["block_type"] for b in blocks]
        assert "paragraph" in types
        assert "unordered_list" in types
        assert "ordered_list" in types
    
    def test_preserves_inline_latex(self):
        md = "The sine ratio $\\sin\\theta = \\frac{opp}{hyp}$ is important."
        blocks = parse_content_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["has_inline_latex"] == True
        assert "$\\sin\\theta" in blocks[0]["verbatim_content"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
