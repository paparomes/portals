"""Google Docs adapter using MCP tools.

This adapter wraps the MCP Google Workspace tools to provide DocumentAdapter
interface without requiring separate OAuth setup.
"""

from __future__ import annotations

import hashlib
import subprocess
import json
from datetime import datetime
from typing import Any

from portals.adapters.base import DocumentAdapter, PlatformURI, RemoteMetadata
from portals.adapters.gdocs.converter import GoogleDocsConverter
from portals.core.exceptions import AdapterError
from portals.core.models import Document, DocumentMetadata


class MCPGoogleDocsAdapter(DocumentAdapter):
    """Google Docs adapter using MCP tools.

    Uses Claude Code's MCP Google Workspace integration, which is already
    authenticated. Provides best-effort formatting using available MCP tools.
    """

    def __init__(self, user_email: str = "rsiepelmeyer@gmail.com"):
        """Initialize MCP-based adapter.

        Args:
            user_email: Google account email
        """
        self.user_email = user_email
        self.converter = GoogleDocsConverter()

    async def read(self, uri: str) -> Document:
        """Read document from Google Docs via MCP.

        Args:
            uri: Google Docs URI

        Returns:
            Document with content and metadata
        """
        try:
            parsed_uri = self.parse_uri(uri)
            doc_id = parsed_uri.identifier

            # Use MCP to get doc content
            # Note: This would need actual MCP tool invocation
            # For now, placeholder
            raise NotImplementedError("MCP read not yet implemented")

        except Exception as e:
            raise AdapterError(f"Failed to read Google Doc {uri}: {e}") from e

    async def write(self, uri: str, doc: Document) -> None:
        """Write document to Google Docs via MCP.

        This applies "best effort" formatting using MCP tools:
        - Bold + font size for headings
        - Bold/italic for emphasis
        - Manual bullet points (not native lists)

        Args:
            uri: Google Docs URI
            doc: Document to write
        """
        try:
            parsed_uri = self.parse_uri(uri)
            doc_id = parsed_uri.identifier

            # Convert markdown
            result = self.converter.markdown_to_gdocs(doc.content)

            # Update document content via MCP
            # This would use mcp__google-workspace__modify_doc_text
            # multiple times to apply formatting
            raise NotImplementedError("MCP write not yet implemented")

        except Exception as e:
            raise AdapterError(f"Failed to write Google Doc {uri}: {e}") from e

    async def get_metadata(self, uri: str) -> RemoteMetadata:
        """Get document metadata via MCP.

        Args:
            uri: Google Docs URI

        Returns:
            RemoteMetadata
        """
        try:
            parsed_uri = self.parse_uri(uri)
            doc_id = parsed_uri.identifier

            # Use MCP inspect_doc_structure for metadata
            raise NotImplementedError("MCP metadata not yet implemented")

        except Exception as e:
            raise AdapterError(f"Failed to get metadata for {uri}: {e}") from e

    async def exists(self, uri: str) -> bool:
        """Check if document exists via MCP.

        Args:
            uri: Google Docs URI

        Returns:
            True if exists
        """
        try:
            metadata = await self.get_metadata(uri)
            return metadata.exists
        except:
            return False

    def parse_uri(self, uri: str) -> PlatformURI:
        """Parse Google Docs URI.

        Args:
            uri: URI string

        Returns:
            Parsed PlatformURI
        """
        if uri.startswith("gdocs://"):
            doc_id = uri[8:]
        elif uri.startswith("https://docs.google.com/document/d/"):
            doc_id = uri.split("/document/d/")[1].split("/")[0]
        else:
            doc_id = uri

        return PlatformURI(
            platform="gdocs",
            identifier=doc_id,
            raw_uri=f"gdocs://{doc_id}"
        )

    async def create(self, uri: str, doc: Document, parent_id: str | None = None) -> str:
        """Create new Google Doc via MCP with best-effort formatting.

        Args:
            uri: URI (unused, title from metadata)
            doc: Document to create
            parent_id: Optional folder ID

        Returns:
            Full URI of created document
        """
        try:
            # Convert markdown
            result = self.converter.markdown_to_gdocs(doc.content)

            # Create doc via MCP with plain text
            # Then apply formatting with multiple modify_doc_text calls
            raise NotImplementedError("MCP create not yet implemented")

        except Exception as e:
            raise AdapterError(f"Failed to create Google Doc: {e}") from e

    async def delete(self, uri: str) -> None:
        """Delete document (not supported via MCP).

        Args:
            uri: Google Docs URI
        """
        raise AdapterError("Delete not supported via MCP tools")
