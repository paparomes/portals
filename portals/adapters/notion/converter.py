"""Converter between Markdown and Notion blocks."""

from __future__ import annotations

import re
from typing import Any


class NotionBlockConverter:
    """Convert between Markdown text and Notion block structures.

    Supports:
    - Paragraphs
    - Headings (h1, h2, h3)
    - Bulleted lists
    - Numbered lists
    - Code blocks
    - Quotes
    """

    def markdown_to_blocks(self, markdown: str) -> list[dict[str, Any]]:
        """Convert markdown text to Notion blocks.

        Args:
            markdown: Markdown text

        Returns:
            List of Notion block objects
        """
        blocks: list[dict[str, Any]] = []
        lines = markdown.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Code blocks (```)
            if line.strip().startswith("```"):
                code_lines = []
                language = line.strip()[3:].strip() or "plain text"
                i += 1

                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1

                code_content = "\n".join(code_lines)
                blocks.append(self._create_code_block(code_content, language))
                i += 1  # Skip closing ```
                continue

            # Headings
            if line.startswith("# "):
                blocks.append(self._create_heading_block(line[2:].strip(), 1))
                i += 1
                continue

            if line.startswith("## "):
                blocks.append(self._create_heading_block(line[3:].strip(), 2))
                i += 1
                continue

            if line.startswith("### "):
                blocks.append(self._create_heading_block(line[4:].strip(), 3))
                i += 1
                continue

            # Quotes
            if line.startswith("> "):
                blocks.append(self._create_quote_block(line[2:].strip()))
                i += 1
                continue

            # Bulleted lists
            if line.strip().startswith("- ") or line.strip().startswith("* "):
                text = line.strip()[2:].strip()
                blocks.append(self._create_bulleted_list_block(text))
                i += 1
                continue

            # Numbered lists (1. 2. etc.)
            if re.match(r"^\d+\.\s", line.strip()):
                text = re.sub(r"^\d+\.\s+", "", line.strip())
                blocks.append(self._create_numbered_list_block(text))
                i += 1
                continue

            # Default to paragraph
            blocks.append(self._create_paragraph_block(line.strip()))
            i += 1

        return blocks

    def blocks_to_markdown(self, blocks: list[dict[str, Any]]) -> str:
        """Convert Notion blocks to markdown text.

        Args:
            blocks: List of Notion block objects

        Returns:
            Markdown text
        """
        markdown_lines: list[str] = []

        for block in blocks:
            block_type = block.get("type")

            if block_type == "paragraph":
                text = self._extract_text_from_rich_text(
                    block.get("paragraph", {}).get("rich_text", [])
                )
                if text:
                    markdown_lines.append(text)
                    markdown_lines.append("")  # Empty line after paragraph

            elif block_type in ("heading_1", "heading_2", "heading_3"):
                level = int(block_type.split("_")[1])
                text = self._extract_text_from_rich_text(
                    block.get(block_type, {}).get("rich_text", [])
                )
                prefix = "#" * level
                markdown_lines.append(f"{prefix} {text}")
                markdown_lines.append("")

            elif block_type == "bulleted_list_item":
                text = self._extract_text_from_rich_text(
                    block.get("bulleted_list_item", {}).get("rich_text", [])
                )
                markdown_lines.append(f"- {text}")

            elif block_type == "numbered_list_item":
                text = self._extract_text_from_rich_text(
                    block.get("numbered_list_item", {}).get("rich_text", [])
                )
                # For simplicity, always use 1. (Markdown handles numbering)
                markdown_lines.append(f"1. {text}")

            elif block_type == "code":
                code_data = block.get("code", {})
                text = self._extract_text_from_rich_text(code_data.get("rich_text", []))
                language = code_data.get("language", "plain text")
                markdown_lines.append(f"```{language}")
                markdown_lines.append(text)
                markdown_lines.append("```")
                markdown_lines.append("")

            elif block_type == "quote":
                text = self._extract_text_from_rich_text(
                    block.get("quote", {}).get("rich_text", [])
                )
                markdown_lines.append(f"> {text}")
                markdown_lines.append("")

        # Join lines and clean up extra newlines
        markdown = "\n".join(markdown_lines)

        # Remove excessive newlines (more than 2 consecutive)
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        return markdown.strip()

    def _create_paragraph_block(self, text: str) -> dict[str, Any]:
        """Create a paragraph block."""
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }

    def _create_heading_block(self, text: str, level: int) -> dict[str, Any]:
        """Create a heading block."""
        heading_type = f"heading_{level}"
        return {
            "object": "block",
            "type": heading_type,
            heading_type: {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }

    def _create_bulleted_list_block(self, text: str) -> dict[str, Any]:
        """Create a bulleted list item block."""
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }

    def _create_numbered_list_block(self, text: str) -> dict[str, Any]:
        """Create a numbered list item block."""
        return {
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }

    def _create_code_block(self, code: str, language: str = "plain text") -> dict[str, Any]:
        """Create a code block."""
        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": code}}],
                "language": language,
            },
        }

    def _create_quote_block(self, text: str) -> dict[str, Any]:
        """Create a quote block."""
        return {
            "object": "block",
            "type": "quote",
            "quote": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }

    def _extract_text_from_rich_text(self, rich_text: list[dict[str, Any]]) -> str:
        """Extract plain text from Notion rich_text array."""
        parts = []
        for item in rich_text:
            if item.get("type") == "text":
                content = item.get("text", {}).get("content", "")
                parts.append(content)
        return "".join(parts)
