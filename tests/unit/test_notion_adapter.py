"""Tests for NotionAdapter."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from portals.adapters.notion.adapter import NotionAdapter
from portals.core.exceptions import NotionError
from portals.core.models import Document, DocumentMetadata


@pytest.fixture
def mock_notion_client() -> MagicMock:
    """Create a mocked Notion client."""
    client = MagicMock()

    # Mock pages API
    client.pages = MagicMock()
    client.pages.retrieve = AsyncMock()
    client.pages.update = AsyncMock()
    client.pages.create = AsyncMock()

    # Mock blocks API
    client.blocks = MagicMock()
    client.blocks.children = MagicMock()
    client.blocks.children.list = AsyncMock()
    client.blocks.children.append = AsyncMock()
    client.blocks.delete = AsyncMock()

    return client


@pytest.fixture
def adapter(mock_notion_client: MagicMock) -> NotionAdapter:
    """Create NotionAdapter with mocked client."""
    with patch("portals.adapters.notion.adapter.AsyncClient", return_value=mock_notion_client):
        adapter = NotionAdapter(api_token="test-token")
        adapter.client = mock_notion_client
        return adapter


@pytest.fixture
def sample_notion_page() -> dict[str, Any]:
    """Create sample Notion page response."""
    return {
        "id": "12345678901234567890123456789012",
        "created_time": "2024-01-01T12:00:00.000Z",
        "last_edited_time": "2024-01-02T12:00:00.000Z",
        "properties": {
            "title": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": "Test Page"},
                    }
                ]
            }
        },
    }


@pytest.fixture
def sample_blocks_response() -> dict[str, Any]:
    """Create sample blocks response."""
    return {
        "results": [
            {
                "id": "block-id-1",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Test content"}}]},
            },
            {
                "id": "block-id-2",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": "Test Heading"}}]},
            },
        ]
    }


class TestNotionAdapter:
    """Tests for NotionAdapter."""

    async def test_read_page(
        self,
        adapter: NotionAdapter,
        mock_notion_client: MagicMock,
        sample_notion_page: dict[str, Any],
        sample_blocks_response: dict[str, Any],
    ) -> None:
        """Test reading a Notion page."""
        # Setup mocks
        mock_notion_client.pages.retrieve.return_value = sample_notion_page
        mock_notion_client.blocks.children.list.return_value = sample_blocks_response

        # Read page
        doc = await adapter.read("notion://12345678901234567890123456789012")

        # Verify calls
        mock_notion_client.pages.retrieve.assert_called_once()
        mock_notion_client.blocks.children.list.assert_called_once()

        # Verify document
        assert doc.metadata.title == "Test Page"
        assert "Test content" in doc.content
        assert "# Test Heading" in doc.content

    async def test_write_page(
        self,
        adapter: NotionAdapter,
        mock_notion_client: MagicMock,
        sample_blocks_response: dict[str, Any],
    ) -> None:
        """Test writing to a Notion page."""
        # Setup mocks
        mock_notion_client.blocks.children.list.return_value = sample_blocks_response

        # Create document
        doc = Document(
            content="# New Content\n\nThis is updated content.",
            metadata=DocumentMetadata(
                title="Updated Title",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            ),
        )

        # Write page
        await adapter.write("notion://12345678901234567890123456789012", doc)

        # Verify update was called
        mock_notion_client.pages.update.assert_called_once()

        # Verify blocks were appended
        assert mock_notion_client.blocks.children.append.called

    async def test_get_metadata(
        self,
        adapter: NotionAdapter,
        mock_notion_client: MagicMock,
        sample_notion_page: dict[str, Any],
        sample_blocks_response: dict[str, Any],
    ) -> None:
        """Test getting page metadata."""
        # Setup mocks
        mock_notion_client.pages.retrieve.return_value = sample_notion_page
        mock_notion_client.blocks.children.list.return_value = sample_blocks_response

        # Get metadata
        metadata = await adapter.get_metadata("notion://12345678901234567890123456789012")

        # Verify metadata
        assert metadata.exists is True
        assert metadata.last_modified == "2024-01-02T12:00:00.000Z"
        assert len(metadata.content_hash) == 64  # SHA-256 hash

    async def test_get_metadata_nonexistent(
        self,
        adapter: NotionAdapter,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test getting metadata for nonexistent page."""
        # Setup mock to raise exception
        mock_notion_client.pages.retrieve.side_effect = Exception("Page not found")

        # Get metadata
        metadata = await adapter.get_metadata("notion://12345678901234567890123456789012")

        # Verify metadata indicates non-existence
        assert metadata.exists is False
        assert metadata.content_hash == ""

    async def test_exists_true(
        self,
        adapter: NotionAdapter,
        mock_notion_client: MagicMock,
        sample_notion_page: dict[str, Any],
    ) -> None:
        """Test checking if page exists (true case)."""
        mock_notion_client.pages.retrieve.return_value = sample_notion_page

        exists = await adapter.exists("notion://12345678901234567890123456789012")

        assert exists is True

    async def test_exists_false(
        self,
        adapter: NotionAdapter,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test checking if page exists (false case)."""
        mock_notion_client.pages.retrieve.side_effect = Exception("Not found")

        exists = await adapter.exists("notion://12345678901234567890123456789012")

        assert exists is False

    def test_parse_uri_with_prefix(self, adapter: NotionAdapter) -> None:
        """Test parsing URI with notion:// prefix."""
        uri = "notion://12345678-1234-1234-1234-123456789012"

        parsed = adapter.parse_uri(uri)

        assert parsed.platform == "notion"
        assert len(parsed.identifier) == 32  # Dashes removed
        assert parsed.raw_uri == uri

    def test_parse_uri_without_prefix(self, adapter: NotionAdapter) -> None:
        """Test parsing URI without prefix."""
        uri = "12345678-1234-1234-1234-123456789012"

        parsed = adapter.parse_uri(uri)

        assert parsed.platform == "notion"
        assert len(parsed.identifier) == 32

    def test_parse_uri_invalid(self, adapter: NotionAdapter) -> None:
        """Test parsing invalid URI."""
        with pytest.raises(ValueError, match="Invalid Notion page ID"):
            adapter.parse_uri("notion://invalid")

    async def test_create_page(
        self,
        adapter: NotionAdapter,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test creating a new page."""
        # Setup mock
        mock_notion_client.pages.create.return_value = {
            "id": "new-page-id-123456789012345678901234"
        }

        # Create document
        doc = Document(
            content="# New Page\n\nContent here.",
            metadata=DocumentMetadata(
                title="New Page",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            ),
        )

        # Create page
        uri = await adapter.create("notion://", doc, parent_id="parent-page-id-123")

        # Verify create was called
        mock_notion_client.pages.create.assert_called_once()

        # Verify URI format
        assert uri.startswith("notion://")
        assert len(uri.split("//")[1]) > 0

    async def test_create_page_without_parent(
        self,
        adapter: NotionAdapter,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test creating page without parent raises error."""
        doc = Document(
            content="# New Page",
            metadata=DocumentMetadata(
                title="New Page",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            ),
        )

        with pytest.raises(NotionError, match="parent_id is required"):
            await adapter.create("notion://", doc)

    async def test_delete_page(
        self,
        adapter: NotionAdapter,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test deleting (archiving) a page."""
        await adapter.delete("notion://12345678901234567890123456789012")

        # Verify archive was called
        mock_notion_client.pages.update.assert_called_once()
        call_args = mock_notion_client.pages.update.call_args
        assert call_args.kwargs["archived"] is True

    async def test_read_page_error(
        self,
        adapter: NotionAdapter,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test reading page with API error."""
        mock_notion_client.pages.retrieve.side_effect = Exception("API Error")

        with pytest.raises(NotionError, match="Failed to read"):
            await adapter.read("notion://12345678901234567890123456789012")

    async def test_write_page_error(
        self,
        adapter: NotionAdapter,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test writing page with API error."""
        mock_notion_client.pages.update.side_effect = Exception("API Error")

        doc = Document(
            content="Content",
            metadata=DocumentMetadata(
                title="Title",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            ),
        )

        with pytest.raises(NotionError, match="Failed to write"):
            await adapter.write("notion://12345678901234567890123456789012", doc)

    async def test_batch_block_append(
        self,
        adapter: NotionAdapter,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test that large content is appended in batches."""
        # Create document with lots of content (>100 blocks)
        lines = [f"Line {i}" for i in range(150)]
        content = "\n".join(lines)

        doc = Document(
            content=content,
            metadata=DocumentMetadata(
                title="Large Document",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            ),
        )

        # Setup mocks
        mock_notion_client.blocks.children.list.return_value = {"results": []}

        # Write page
        await adapter.write("notion://12345678901234567890123456789012", doc)

        # Verify multiple batch appends were called
        assert mock_notion_client.blocks.children.append.call_count >= 2

    async def test_extract_metadata_with_tags(
        self,
        adapter: NotionAdapter,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test extracting metadata with tags from multi-select."""
        page_with_tags = {
            "id": "test-id",
            "created_time": "2024-01-01T12:00:00.000Z",
            "last_edited_time": "2024-01-02T12:00:00.000Z",
            "properties": {
                "title": {"title": [{"type": "text", "text": {"content": "Test"}}]},
                "Tags": {
                    "type": "multi_select",
                    "multi_select": [
                        {"name": "tag1"},
                        {"name": "tag2"},
                    ],
                },
            },
        }

        mock_notion_client.pages.retrieve.return_value = page_with_tags
        mock_notion_client.blocks.children.list.return_value = {"results": []}

        doc = await adapter.read("notion://12345678901234567890123456789012")

        assert "tag1" in doc.metadata.tags
        assert "tag2" in doc.metadata.tags

    def test_initialization(self) -> None:
        """Test adapter initialization."""
        with patch("portals.adapters.notion.adapter.AsyncClient") as mock_client_class:
            adapter = NotionAdapter(api_token="test-token-123")

            # Verify client was created with token
            mock_client_class.assert_called_once_with(auth="test-token-123")

            # Verify converter was initialized
            assert adapter.converter is not None
