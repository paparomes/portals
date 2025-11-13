"""Convert between Markdown and Google Docs format."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token


@dataclass
class FormatRange:
    """A range of text with formatting information."""

    start_index: int
    end_index: int
    format_type: str  # "heading", "bold", "italic", "link", etc.
    level: int | None = None  # For headings (1-6)
    url: str | None = None  # For links
    text: str | None = None  # Original text


@dataclass
class ConversionResult:
    """Result of markdown to Google Docs conversion."""

    plain_text: str  # Text without markdown symbols
    format_ranges: list[FormatRange] = field(default_factory=list)
    list_ranges: list[dict[str, Any]] = field(default_factory=list)


class GoogleDocsConverter:
    """Convert between Markdown and Google Docs format.

    Uses markdown-it-py for parsing and generates Google Docs API batch requests.
    """

    def __init__(self):
        """Initialize converter."""
        self.md = MarkdownIt()
        self.current_index = 1  # Google Docs starts at index 1

    def markdown_to_gdocs(self, markdown: str) -> ConversionResult:
        """Convert markdown to Google Docs format.

        Args:
            markdown: Markdown text

        Returns:
            ConversionResult with plain text and formatting information
        """
        # Parse markdown
        tokens = self.md.parse(markdown)

        # Convert to plain text and track formatting
        result = ConversionResult(plain_text="")
        self.current_index = 1  # Reset index

        self._process_tokens(tokens, result)

        return result

    def _process_tokens(
        self,
        tokens: list[Token],
        result: ConversionResult,
        parent_type: str | None = None,
    ) -> None:
        """Process markdown tokens and build plain text + formatting.

        Args:
            tokens: List of markdown-it tokens
            result: ConversionResult to populate
            parent_type: Parent token type for context
        """
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.type == "heading_open":
                i = self._process_heading(tokens, i, result)
            elif token.type == "paragraph_open":
                i = self._process_paragraph(tokens, i, result)
            elif token.type == "bullet_list_open":
                i = self._process_list(tokens, i, result, ordered=False)
            elif token.type == "ordered_list_open":
                i = self._process_list(tokens, i, result, ordered=True)
            elif token.type == "blockquote_open":
                i = self._process_blockquote(tokens, i, result)
            elif token.type == "code_block":
                i = self._process_code_block(token, i, result)
            elif token.type == "fence":
                i = self._process_code_block(token, i, result)
            elif token.type == "hr":
                i = self._process_hr(token, i, result)
            else:
                i += 1

        return

    def _process_heading(
        self,
        tokens: list[Token],
        index: int,
        result: ConversionResult,
    ) -> int:
        """Process heading tokens.

        Args:
            tokens: Token list
            index: Current index
            result: Result to update

        Returns:
            New index after processing
        """
        open_token = tokens[index]
        level = int(open_token.tag[1])  # h1 -> 1, h2 -> 2, etc.

        start_index = self.current_index
        text = ""

        # Process inline content
        i = index + 1
        while i < len(tokens) and tokens[i].type != "heading_close":
            if tokens[i].type == "inline":
                text_content = self._process_inline(tokens[i], result)
                text += text_content
                self.current_index += len(text_content)
            i += 1

        end_index = self.current_index

        # Add newline after heading
        text += "\n"
        self.current_index += 1

        result.plain_text += text

        # Track heading range
        result.format_ranges.append(
            FormatRange(
                start_index=start_index,
                end_index=end_index,
                format_type="heading",
                level=level,
                text=text.strip(),
            )
        )

        return i + 1  # Skip closing token

    def _process_paragraph(
        self,
        tokens: list[Token],
        index: int,
        result: ConversionResult,
    ) -> int:
        """Process paragraph tokens.

        Args:
            tokens: Token list
            index: Current index
            result: Result to update

        Returns:
            New index after processing
        """
        text = ""

        # Process inline content
        i = index + 1
        while i < len(tokens) and tokens[i].type != "paragraph_close":
            if tokens[i].type == "inline":
                text_content = self._process_inline(tokens[i], result)
                text += text_content
                self.current_index += len(text_content)
            i += 1

        # Add newline after paragraph
        text += "\n"
        self.current_index += 1

        result.plain_text += text

        return i + 1  # Skip closing token

    def _process_inline(self, token: Token, result: ConversionResult) -> str:
        """Process inline tokens (bold, italic, links, etc.).

        Args:
            token: Inline token
            result: Result to update

        Returns:
            Plain text content
        """
        if not token.children:
            return ""

        text = ""
        i = 0
        while i < len(token.children):
            child = token.children[i]

            if child.type == "text":
                text += child.content
                i += 1
            elif child.type == "strong_open":
                # Track start of bold
                start_index = self.current_index + len(text)
                bold_text, skip_count = self._get_text_and_skip_count(token.children, i, "strong_close")
                result.format_ranges.append(
                    FormatRange(
                        start_index=start_index,
                        end_index=start_index + len(bold_text),
                        format_type="bold",
                        text=bold_text,
                    )
                )
                text += bold_text
                i += skip_count
            elif child.type == "em_open":
                # Track start of italic
                start_index = self.current_index + len(text)
                italic_text, skip_count = self._get_text_and_skip_count(token.children, i, "em_close")
                result.format_ranges.append(
                    FormatRange(
                        start_index=start_index,
                        end_index=start_index + len(italic_text),
                        format_type="italic",
                        text=italic_text,
                    )
                )
                text += italic_text
                i += skip_count
            elif child.type == "code_inline":
                # Inline code
                start_index = self.current_index + len(text)
                code_text = child.content
                result.format_ranges.append(
                    FormatRange(
                        start_index=start_index,
                        end_index=start_index + len(code_text),
                        format_type="code_inline",
                        text=code_text,
                    )
                )
                text += code_text
                i += 1
            elif child.type == "link_open":
                # Track link
                start_index = self.current_index + len(text)
                link_url = child.attrs.get("href", "") if child.attrs else ""
                link_text, skip_count = self._get_text_and_skip_count(token.children, i, "link_close")
                result.format_ranges.append(
                    FormatRange(
                        start_index=start_index,
                        end_index=start_index + len(link_text),
                        format_type="link",
                        url=link_url,
                        text=link_text,
                    )
                )
                text += link_text
                i += skip_count
            elif child.type in ["strong_close", "em_close", "link_close"]:
                # Skip closing tokens (already handled)
                i += 1
            else:
                i += 1

        return text

    def _get_text_and_skip_count(
        self,
        siblings: list[Token],
        start_index: int,
        close_type: str,
    ) -> tuple[str, int]:
        """Get text content until matching close token and count tokens to skip.

        Args:
            siblings: Sibling tokens
            start_index: Index of open token
            close_type: Close token type to find

        Returns:
            Tuple of (text content, number of tokens to skip including close token)
        """
        text = ""
        i = start_index + 1

        while i < len(siblings) and siblings[i].type != close_type:
            if siblings[i].type == "text":
                text += siblings[i].content
            i += 1

        # Return text and count of tokens to skip (including close token)
        skip_count = i - start_index + 1
        return text, skip_count

    def _process_list(
        self,
        tokens: list[Token],
        index: int,
        result: ConversionResult,
        ordered: bool = False,
    ) -> int:
        """Process list tokens.

        Args:
            tokens: Token list
            index: Current index
            result: Result to update
            ordered: True for numbered lists

        Returns:
            New index after processing
        """
        list_start = self.current_index

        i = index + 1
        while i < len(tokens) and tokens[i].type not in ["bullet_list_close", "ordered_list_close"]:
            if tokens[i].type == "list_item_open":
                item_start = self.current_index

                # Process list item content
                i += 1
                while i < len(tokens) and tokens[i].type != "list_item_close":
                    if tokens[i].type == "paragraph_open":
                        # Get paragraph content but don't add extra newline
                        i += 1
                        while i < len(tokens) and tokens[i].type != "paragraph_close":
                            if tokens[i].type == "inline":
                                text_content = self._process_inline(tokens[i], result)
                                result.plain_text += text_content
                                self.current_index += len(text_content)
                            i += 1
                    i += 1

                # Add newline after list item
                result.plain_text += "\n"
                self.current_index += 1

                item_end = self.current_index

                # Track list item range
                result.list_ranges.append({
                    "start_index": item_start,
                    "end_index": item_end,
                    "ordered": ordered,
                })
            i += 1

        return i + 1

    def _process_blockquote(
        self,
        tokens: list[Token],
        index: int,
        result: ConversionResult,
    ) -> int:
        """Process blockquote tokens.

        Args:
            tokens: Token list
            index: Current index
            result: Result to update

        Returns:
            New index after processing
        """
        # For now, just process as normal text with "> " prefix
        result.plain_text += "> "
        self.current_index += 2

        i = index + 1
        while i < len(tokens) and tokens[i].type != "blockquote_close":
            if tokens[i].type == "paragraph_open":
                i = self._process_paragraph(tokens, i, result)
            else:
                i += 1

        return i

    def _process_code_block(
        self,
        token: Token,
        index: int,
        result: ConversionResult,
    ) -> int:
        """Process code block tokens.

        Args:
            token: Code block token
            index: Current index
            result: Result to update

        Returns:
            New index after processing
        """
        start_index = self.current_index
        code_text = token.content

        result.plain_text += code_text + "\n"
        self.current_index += len(code_text) + 1

        # Track code block range
        result.format_ranges.append(
            FormatRange(
                start_index=start_index,
                end_index=self.current_index - 1,
                format_type="code_block",
                text=code_text,
            )
        )

        return index + 1

    def _process_hr(
        self,
        token: Token,
        index: int,
        result: ConversionResult,
    ) -> int:
        """Process horizontal rule tokens.

        Args:
            token: HR token
            index: Current index
            result: Result to update

        Returns:
            New index after processing
        """
        # Add horizontal line as separator
        result.plain_text += "---\n"
        self.current_index += 4

        return index + 1

    def generate_batch_requests(self, conversion: ConversionResult) -> list[dict[str, Any]]:
        """Generate Google Docs API batch update requests.

        Args:
            conversion: Conversion result with formatting info

        Returns:
            List of batch update request dictionaries
        """
        requests = []

        # Apply heading styles
        for fmt in conversion.format_ranges:
            if fmt.format_type == "heading":
                requests.append({
                    "updateParagraphStyle": {
                        "range": {
                            "startIndex": fmt.start_index,
                            "endIndex": fmt.end_index,
                        },
                        "paragraphStyle": {
                            "namedStyleType": f"HEADING_{fmt.level}"
                        },
                        "fields": "namedStyleType",
                    }
                })

            elif fmt.format_type == "bold":
                requests.append({
                    "updateTextStyle": {
                        "range": {
                            "startIndex": fmt.start_index,
                            "endIndex": fmt.end_index,
                        },
                        "textStyle": {"bold": True},
                        "fields": "bold",
                    }
                })

            elif fmt.format_type == "italic":
                requests.append({
                    "updateTextStyle": {
                        "range": {
                            "startIndex": fmt.start_index,
                            "endIndex": fmt.end_index,
                        },
                        "textStyle": {"italic": True},
                        "fields": "italic",
                    }
                })

            elif fmt.format_type == "code_inline":
                requests.append({
                    "updateTextStyle": {
                        "range": {
                            "startIndex": fmt.start_index,
                            "endIndex": fmt.end_index,
                        },
                        "textStyle": {
                            "fontFamily": "Courier New",
                            "fontSize": {"magnitude": 10, "unit": "PT"},
                        },
                        "fields": "fontFamily,fontSize",
                    }
                })

            elif fmt.format_type == "link":
                requests.append({
                    "updateTextStyle": {
                        "range": {
                            "startIndex": fmt.start_index,
                            "endIndex": fmt.end_index,
                        },
                        "textStyle": {
                            "link": {"url": fmt.url}
                        },
                        "fields": "link",
                    }
                })

        # Apply list formatting
        for list_range in conversion.list_ranges:
            bullet_preset = "NUMBERED_DECIMAL_ALPHA_ROMAN" if list_range["ordered"] else "BULLET_DISC_CIRCLE_SQUARE"
            requests.append({
                "createParagraphBullets": {
                    "range": {
                        "startIndex": list_range["start_index"],
                        "endIndex": list_range["end_index"] - 1,  # Exclude trailing newline
                    },
                    "bulletPreset": bullet_preset,
                }
            })

        return requests
