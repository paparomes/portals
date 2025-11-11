"""Tests for NotionBlockConverter."""

from __future__ import annotations

from typing import Any

from portals.adapters.notion.converter import NotionBlockConverter


class TestNotionBlockConverter:
    """Tests for NotionBlockConverter."""

    def test_paragraph_to_block(self) -> None:
        """Test converting paragraph to Notion block."""
        converter = NotionBlockConverter()
        markdown = "This is a simple paragraph."

        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "paragraph"
        assert blocks[0]["paragraph"]["rich_text"][0]["text"]["content"] == markdown

    def test_heading1_to_block(self) -> None:
        """Test converting heading 1 to Notion block."""
        converter = NotionBlockConverter()
        markdown = "# Heading 1"

        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_1"
        assert blocks[0]["heading_1"]["rich_text"][0]["text"]["content"] == "Heading 1"

    def test_heading2_to_block(self) -> None:
        """Test converting heading 2 to Notion block."""
        converter = NotionBlockConverter()
        markdown = "## Heading 2"

        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_2"
        assert blocks[0]["heading_2"]["rich_text"][0]["text"]["content"] == "Heading 2"

    def test_heading3_to_block(self) -> None:
        """Test converting heading 3 to Notion block."""
        converter = NotionBlockConverter()
        markdown = "### Heading 3"

        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_3"
        assert blocks[0]["heading_3"]["rich_text"][0]["text"]["content"] == "Heading 3"

    def test_bulleted_list_to_block(self) -> None:
        """Test converting bulleted list to Notion blocks."""
        converter = NotionBlockConverter()
        markdown = "- Item 1\n- Item 2\n- Item 3"

        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 3
        for i, block in enumerate(blocks):
            assert block["type"] == "bulleted_list_item"
            expected_text = f"Item {i + 1}"
            assert block["bulleted_list_item"]["rich_text"][0]["text"]["content"] == expected_text

    def test_numbered_list_to_block(self) -> None:
        """Test converting numbered list to Notion blocks."""
        converter = NotionBlockConverter()
        markdown = "1. First\n2. Second\n3. Third"

        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 3
        expected_texts = ["First", "Second", "Third"]
        for i, block in enumerate(blocks):
            assert block["type"] == "numbered_list_item"
            assert (
                block["numbered_list_item"]["rich_text"][0]["text"]["content"] == expected_texts[i]
            )

    def test_code_block_to_block(self) -> None:
        """Test converting code block to Notion block."""
        converter = NotionBlockConverter()
        markdown = "```python\nprint('Hello, world!')\n```"

        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "python"
        assert blocks[0]["code"]["rich_text"][0]["text"]["content"] == "print('Hello, world!')"

    def test_quote_to_block(self) -> None:
        """Test converting quote to Notion block."""
        converter = NotionBlockConverter()
        markdown = "> This is a quote"

        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "quote"
        assert blocks[0]["quote"]["rich_text"][0]["text"]["content"] == "This is a quote"

    def test_block_to_markdown_paragraph(self) -> None:
        """Test converting Notion paragraph block to markdown."""
        converter = NotionBlockConverter()
        blocks = [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": "Test paragraph"}}]
                },
            }
        ]

        markdown = converter.blocks_to_markdown(blocks)

        assert markdown == "Test paragraph"

    def test_block_to_markdown_heading1(self) -> None:
        """Test converting Notion heading 1 block to markdown."""
        converter = NotionBlockConverter()
        blocks = [
            {
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": "My Heading"}}]},
            }
        ]

        markdown = converter.blocks_to_markdown(blocks)

        assert markdown == "# My Heading"

    def test_block_to_markdown_heading2(self) -> None:
        """Test converting Notion heading 2 block to markdown."""
        converter = NotionBlockConverter()
        blocks = [
            {
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "My Heading"}}]},
            }
        ]

        markdown = converter.blocks_to_markdown(blocks)

        assert markdown == "## My Heading"

    def test_block_to_markdown_bulleted_list(self) -> None:
        """Test converting Notion bulleted list blocks to markdown."""
        converter = NotionBlockConverter()
        blocks = [
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": "Item 1"}}]
                },
            },
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": "Item 2"}}]
                },
            },
        ]

        markdown = converter.blocks_to_markdown(blocks)

        assert "- Item 1" in markdown
        assert "- Item 2" in markdown

    def test_block_to_markdown_code(self) -> None:
        """Test converting Notion code block to markdown."""
        converter = NotionBlockConverter()
        blocks = [
            {
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": "def foo():\n    pass"}}],
                    "language": "python",
                },
            }
        ]

        markdown = converter.blocks_to_markdown(blocks)

        assert "```python" in markdown
        assert "def foo():" in markdown
        assert "pass" in markdown
        assert "```" in markdown

    def test_block_to_markdown_quote(self) -> None:
        """Test converting Notion quote block to markdown."""
        converter = NotionBlockConverter()
        blocks = [
            {
                "type": "quote",
                "quote": {"rich_text": [{"type": "text", "text": {"content": "A quote"}}]},
            }
        ]

        markdown = converter.blocks_to_markdown(blocks)

        assert "> A quote" in markdown

    def test_mixed_content_to_blocks(self) -> None:
        """Test converting mixed content to Notion blocks."""
        converter = NotionBlockConverter()
        markdown = """# Title

This is a paragraph.

## Section

- Item 1
- Item 2

```python
print('Hello')
```

> A quote"""

        blocks = converter.markdown_to_blocks(markdown)

        # Should have heading, paragraph, heading, 2 list items, code, quote
        assert len(blocks) >= 7

        types = [b["type"] for b in blocks]
        assert "heading_1" in types
        assert "heading_2" in types
        assert "paragraph" in types
        assert "bulleted_list_item" in types
        assert "code" in types
        assert "quote" in types

    def test_round_trip_conversion(self) -> None:
        """Test converting markdown to blocks and back to markdown."""
        converter = NotionBlockConverter()
        original_markdown = """# Main Title

This is a paragraph with some content.

## Subsection

- First item
- Second item

```python
def hello():
    print("Hello, world!")
```

> This is a quote"""

        # Convert to blocks
        blocks = converter.markdown_to_blocks(original_markdown)

        # Convert back to markdown
        result_markdown = converter.blocks_to_markdown(blocks)

        # Check key elements are preserved
        assert "# Main Title" in result_markdown
        assert "## Subsection" in result_markdown
        assert "- First item" in result_markdown
        assert "- Second item" in result_markdown
        assert "```python" in result_markdown
        assert "def hello():" in result_markdown
        assert "> This is a quote" in result_markdown

    def test_empty_markdown(self) -> None:
        """Test converting empty markdown."""
        converter = NotionBlockConverter()
        markdown = ""

        blocks = converter.markdown_to_blocks(markdown)

        assert blocks == []

    def test_empty_blocks(self) -> None:
        """Test converting empty blocks list."""
        converter = NotionBlockConverter()
        blocks: list[dict[str, Any]] = []

        markdown = converter.blocks_to_markdown(blocks)

        assert markdown == ""

    def test_skip_empty_lines(self) -> None:
        """Test that empty lines are skipped in markdown."""
        converter = NotionBlockConverter()
        markdown = "Line 1\n\n\nLine 2"

        blocks = converter.markdown_to_blocks(markdown)

        # Should have 2 paragraphs, empty lines skipped
        assert len(blocks) == 2

    def test_code_block_without_language(self) -> None:
        """Test code block without specified language."""
        converter = NotionBlockConverter()
        markdown = "```\nsome code\n```"

        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "plain text"

    def test_asterisk_bullet_points(self) -> None:
        """Test bullet points with asterisks."""
        converter = NotionBlockConverter()
        markdown = "* Item with asterisk\n* Another item"

        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 2
        assert all(b["type"] == "bulleted_list_item" for b in blocks)

    def test_multiline_code_block(self) -> None:
        """Test code block with multiple lines."""
        converter = NotionBlockConverter()
        markdown = """```python
def foo():
    return 42

def bar():
    return "test"
```"""

        blocks = converter.markdown_to_blocks(markdown)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "code"
        content = blocks[0]["code"]["rich_text"][0]["text"]["content"]
        assert "def foo():" in content
        assert "def bar():" in content
