"""Notion adapter for reading and writing pages."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from notion_client import AsyncClient

from portals.adapters.base import DocumentAdapter, PlatformURI, RemoteMetadata
from portals.adapters.notion.converter import NotionBlockConverter
from portals.core.exceptions import NotionError
from portals.core.models import Document, DocumentMetadata


class NotionAdapter(DocumentAdapter):
    """Adapter for Notion pages.

    Handles reading and writing Notion pages, converting between
    markdown and Notion block structures.
    """

    def __init__(self, api_token: str) -> None:
        """Initialize Notion adapter.

        Args:
            api_token: Notion API integration token
        """
        self.client = AsyncClient(auth=api_token)
        self.converter = NotionBlockConverter()

    async def read(self, uri: str) -> Document:
        """Read Notion page and convert to Document.

        Args:
            uri: Notion URI (e.g., "notion://page-id")

        Returns:
            Document object with content and metadata

        Raises:
            NotionError: If page cannot be read
        """
        try:
            parsed_uri = self.parse_uri(uri)
            page_id = parsed_uri.identifier

            # Fetch page metadata
            page = await self.client.pages.retrieve(page_id=page_id)

            # Fetch page content (blocks)
            blocks_response = await self.client.blocks.children.list(block_id=page_id)
            blocks = blocks_response.get("results", [])

            # Convert blocks to markdown
            markdown_content = self.converter.blocks_to_markdown(blocks)

            # Extract metadata
            metadata = self._extract_metadata(page)

            # Calculate content hash (done by caller usually, but we can set it)
            return Document(
                content=markdown_content,
                metadata=metadata,
            )

        except NotionError:
            raise
        except Exception as e:
            raise NotionError(f"Failed to read Notion page {uri}: {e}") from e

    async def write(self, uri: str, doc: Document) -> None:
        """Write Document to Notion page.

        Args:
            uri: Notion URI
            doc: Document to write

        Raises:
            NotionError: If page cannot be written
        """
        try:
            parsed_uri = self.parse_uri(uri)
            page_id = parsed_uri.identifier

            # Update page properties (title)
            await self.client.pages.update(
                page_id=page_id,
                properties={
                    "title": {"title": [{"type": "text", "text": {"content": doc.metadata.title}}]}
                },
            )

            # Delete existing blocks
            await self._delete_all_blocks(page_id)

            # Convert markdown to blocks
            blocks = self.converter.markdown_to_blocks(doc.content)

            # Append new blocks (Notion API has a 100 block limit per request)
            await self._append_blocks_in_batches(page_id, blocks)

        except NotionError:
            raise
        except Exception as e:
            raise NotionError(f"Failed to write to Notion page {uri}: {e}") from e

    async def get_metadata(self, uri: str) -> RemoteMetadata:
        """Get Notion page metadata without reading full content.

        Args:
            uri: Notion URI

        Returns:
            RemoteMetadata with hash and timestamp

        Raises:
            NotionError: If metadata cannot be retrieved
        """
        try:
            parsed_uri = self.parse_uri(uri)
            page_id = parsed_uri.identifier

            # Fetch page metadata
            page = await self.client.pages.retrieve(page_id=page_id)

            # Get last edited time
            last_edited = page.get("last_edited_time", "")

            # For content hash, we'd need to fetch blocks
            # For now, use last_edited_time as a proxy
            # In real implementation, might want to fetch and hash actual content
            blocks_response = await self.client.blocks.children.list(block_id=page_id)
            blocks = blocks_response.get("results", [])
            markdown = self.converter.blocks_to_markdown(blocks)

            # Calculate hash
            import hashlib

            content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

            return RemoteMetadata(
                uri=uri,
                content_hash=content_hash,
                last_modified=last_edited,
                exists=True,
            )

        except Exception:
            # If page doesn't exist or can't be accessed
            return RemoteMetadata(
                uri=uri,
                content_hash="",
                last_modified="",
                exists=False,
            )

    async def exists(self, uri: str) -> bool:
        """Check if Notion page exists.

        Args:
            uri: Notion URI

        Returns:
            True if page exists, False otherwise
        """
        try:
            parsed_uri = self.parse_uri(uri)
            page_id = parsed_uri.identifier

            await self.client.pages.retrieve(page_id=page_id)
            return True

        except Exception:
            return False

    def parse_uri(self, uri: str) -> PlatformURI:
        """Parse Notion URI.

        Args:
            uri: URI string (e.g., "notion://page-id" or just "page-id")

        Returns:
            Parsed PlatformURI object

        Raises:
            ValueError: If URI is invalid
        """
        # Remove notion:// prefix if present
        if uri.startswith("notion://"):
            page_id = uri[9:]
        else:
            page_id = uri

        # Basic validation - Notion page IDs are UUIDs with dashes removed
        # They're 32 hex characters
        page_id = page_id.replace("-", "")

        if not page_id or len(page_id) != 32:
            raise ValueError(f"Invalid Notion page ID: {uri}")

        return PlatformURI(
            platform="notion",
            identifier=page_id,
            raw_uri=uri,
        )

    async def create(self, uri: str, doc: Document, parent_id: str | None = None) -> str:
        """Create new Notion page.

        Args:
            uri: URI (can be partial, just a title)
            doc: Document to create
            parent_id: Parent page ID for nested pages

        Returns:
            Full URI of created page

        Raises:
            NotionError: If page cannot be created
        """
        try:
            # Prepare page properties
            properties = {
                "title": {"title": [{"type": "text", "text": {"content": doc.metadata.title}}]}
            }

            # Prepare parent
            parent: dict[str, Any]
            if parent_id:
                parent = {"type": "page_id", "page_id": parent_id}
            else:
                # Need to specify a parent - either page_id or database_id
                # For now, require parent_id
                raise NotionError("parent_id is required for creating Notion pages")

            # Convert markdown to blocks
            children = self.converter.markdown_to_blocks(doc.content)

            # Create page (with up to 100 blocks initially)
            initial_blocks = children[:100]
            remaining_blocks = children[100:]

            page = await self.client.pages.create(
                parent=parent,
                properties=properties,
                children=initial_blocks,
            )

            page_id = page["id"]

            # Append remaining blocks if any
            if remaining_blocks:
                await self._append_blocks_in_batches(page_id, remaining_blocks)

            return f"notion://{page_id}"

        except NotionError:
            raise
        except Exception as e:
            raise NotionError(f"Failed to create Notion page: {e}") from e

    async def delete(self, uri: str) -> None:
        """Archive Notion page.

        Note: Notion doesn't support true deletion via API, only archiving.

        Args:
            uri: Notion URI

        Raises:
            NotionError: If page cannot be archived
        """
        try:
            parsed_uri = self.parse_uri(uri)
            page_id = parsed_uri.identifier

            # Archive page (Notion's version of delete)
            await self.client.pages.update(
                page_id=page_id,
                archived=True,
            )

        except Exception as e:
            raise NotionError(f"Failed to archive Notion page {uri}: {e}") from e

    async def _delete_all_blocks(self, page_id: str) -> None:
        """Delete all blocks from a page.

        Args:
            page_id: Page ID to clear
        """
        # Fetch all blocks
        blocks_response = await self.client.blocks.children.list(block_id=page_id)
        blocks = blocks_response.get("results", [])

        # Delete each block
        for block in blocks:
            block_id = block["id"]
            await self.client.blocks.delete(block_id=block_id)

    async def _append_blocks_in_batches(
        self, page_id: str, blocks: list[dict[str, Any]], batch_size: int = 100
    ) -> None:
        """Append blocks to a page in batches.

        Notion API limits block appends to 100 per request.

        Args:
            page_id: Page ID to append to
            blocks: List of block objects
            batch_size: Maximum blocks per batch (default 100)
        """
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i : i + batch_size]
            await self.client.blocks.children.append(
                block_id=page_id,
                children=batch,
            )

    def _extract_metadata(self, page: dict[str, Any]) -> DocumentMetadata:
        """Extract metadata from Notion page object.

        Args:
            page: Notion page object

        Returns:
            DocumentMetadata object
        """
        # Extract title from properties
        title = "Untitled"
        properties = page.get("properties", {})

        if "title" in properties:
            title_prop = properties["title"]
            if title_prop.get("title"):
                title_texts = title_prop["title"]
                if title_texts and len(title_texts) > 0:
                    title = title_texts[0].get("text", {}).get("content", "Untitled")

        # Extract timestamps
        created_time = page.get("created_time", "")
        last_edited_time = page.get("last_edited_time", "")

        # Parse timestamps
        created_at = (
            datetime.fromisoformat(created_time.replace("Z", "+00:00"))
            if created_time
            else datetime.now()
        )
        modified_at = (
            datetime.fromisoformat(last_edited_time.replace("Z", "+00:00"))
            if last_edited_time
            else datetime.now()
        )

        # Extract other properties as tags/properties
        tags = []
        properties_dict = {}

        for prop_name, prop_value in properties.items():
            if prop_name == "title":
                continue

            prop_type = prop_value.get("type")

            # Handle multi-select as tags
            if prop_type == "multi_select":
                options = prop_value.get("multi_select", [])
                tags.extend([opt["name"] for opt in options])

            # Store other properties
            else:
                properties_dict[prop_name] = prop_value

        return DocumentMetadata(
            title=title,
            created_at=created_at,
            modified_at=modified_at,
            tags=tags,
            properties=properties_dict,
        )
