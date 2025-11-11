"""Local file system adapter for markdown files."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import frontmatter

from portals.adapters.base import DocumentAdapter, PlatformURI, RemoteMetadata
from portals.core.exceptions import LocalFileError
from portals.core.models import Document, DocumentMetadata


class LocalFileAdapter(DocumentAdapter):
    """Adapter for local markdown files with YAML front matter.

    Handles reading and writing markdown files from the local filesystem.
    Supports YAML front matter for metadata storage.
    """

    def __init__(self, base_path: str | None = None) -> None:
        """Initialize local file adapter.

        Args:
            base_path: Optional base path for relative file paths
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()

    async def read(self, uri: str) -> Document:
        """Read markdown file from local filesystem.

        Args:
            uri: File URI (e.g., "file:///path/to/file.md" or "/path/to/file.md")

        Returns:
            Document object with content and metadata

        Raises:
            LocalFileError: If file cannot be read
        """
        try:
            file_path = self._uri_to_path(uri)

            if not file_path.exists():
                raise LocalFileError(f"File not found: {file_path}")

            if not file_path.is_file():
                raise LocalFileError(f"Not a file: {file_path}")

            # Read file content
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()

            # Parse front matter
            post = frontmatter.loads(content)

            # Extract metadata from front matter
            metadata = self._extract_metadata(post.metadata, file_path)

            # Calculate content hash
            content_hash = self._calculate_hash(post.content)

            return Document(
                content=post.content,
                metadata=metadata,
                content_hash=content_hash,
            )

        except LocalFileError:
            raise
        except Exception as e:
            raise LocalFileError(f"Failed to read file {uri}: {e}") from e

    async def write(self, uri: str, doc: Document) -> None:
        """Write markdown file to local filesystem.

        Args:
            uri: File URI
            doc: Document to write

        Raises:
            LocalFileError: If file cannot be written
        """
        try:
            file_path = self._uri_to_path(uri)

            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare front matter
            metadata_dict = {
                "title": doc.metadata.title,
                "created_at": doc.metadata.created_at.isoformat(),
                "modified_at": doc.metadata.modified_at.isoformat(),
                "tags": doc.metadata.tags,
                **doc.metadata.properties,
            }

            # Create post with front matter
            post = frontmatter.Post(doc.content, **metadata_dict)

            # Write to file
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(frontmatter.dumps(post))

        except Exception as e:
            raise LocalFileError(f"Failed to write file {uri}: {e}") from e

    async def get_metadata(self, uri: str) -> RemoteMetadata:
        """Get file metadata without reading full content.

        Args:
            uri: File URI

        Returns:
            RemoteMetadata with hash and timestamp

        Raises:
            LocalFileError: If metadata cannot be retrieved
        """
        try:
            file_path = self._uri_to_path(uri)

            if not file_path.exists():
                return RemoteMetadata(
                    uri=uri,
                    content_hash="",
                    last_modified="",
                    exists=False,
                )

            # Read file for hash calculation
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()

            # Parse to get just content (without front matter)
            post = frontmatter.loads(content)
            content_hash = self._calculate_hash(post.content)

            # Get file modification time
            stat = file_path.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

            return RemoteMetadata(
                uri=uri,
                content_hash=content_hash,
                last_modified=last_modified,
                exists=True,
            )

        except Exception as e:
            raise LocalFileError(f"Failed to get metadata for {uri}: {e}") from e

    async def exists(self, uri: str) -> bool:
        """Check if file exists.

        Args:
            uri: File URI

        Returns:
            True if file exists, False otherwise
        """
        try:
            file_path = self._uri_to_path(uri)
            return file_path.exists() and file_path.is_file()
        except Exception:
            return False

    def parse_uri(self, uri: str) -> PlatformURI:
        """Parse file URI.

        Args:
            uri: URI string to parse (e.g., "file:///path/to/file.md" or "/path/to/file.md")

        Returns:
            Parsed PlatformURI object

        Raises:
            ValueError: If URI is invalid
        """
        # Remove file:// prefix if present
        if uri.startswith("file://"):
            path_str = uri[7:]
        else:
            path_str = uri

        try:
            path = Path(path_str)
            return PlatformURI(
                platform="file",
                identifier=str(path.absolute()),
                raw_uri=uri,
            )
        except Exception as e:
            raise ValueError(f"Invalid file URI: {uri}") from e

    async def create(self, uri: str, doc: Document, parent_id: str | None = None) -> str:
        """Create new file.

        Args:
            uri: File URI (filename or path)
            doc: Document to create
            parent_id: Ignored for local files

        Returns:
            Full URI of created file

        Raises:
            LocalFileError: If file cannot be created
        """
        try:
            file_path = self._uri_to_path(uri)

            if file_path.exists():
                raise LocalFileError(f"File already exists: {file_path}")

            # Write the file
            await self.write(uri, doc)

            # Return full URI
            return f"file://{file_path.absolute()}"

        except LocalFileError:
            raise
        except Exception as e:
            raise LocalFileError(f"Failed to create file {uri}: {e}") from e

    async def delete(self, uri: str) -> None:
        """Delete file.

        Args:
            uri: File URI

        Raises:
            LocalFileError: If file cannot be deleted
        """
        try:
            file_path = self._uri_to_path(uri)

            if not file_path.exists():
                raise LocalFileError(f"File not found: {file_path}")

            file_path.unlink()

        except LocalFileError:
            raise
        except Exception as e:
            raise LocalFileError(f"Failed to delete file {uri}: {e}") from e

    def _uri_to_path(self, uri: str) -> Path:
        """Convert URI to Path object.

        Args:
            uri: File URI

        Returns:
            Path object
        """
        # Remove file:// prefix if present
        if uri.startswith("file://"):
            path_str = uri[7:]
        else:
            path_str = uri

        path = Path(path_str)

        # If relative path, resolve against base_path
        if not path.is_absolute():
            path = self.base_path / path

        return path

    def _extract_metadata(self, front_matter: dict[str, Any], file_path: Path) -> DocumentMetadata:
        """Extract metadata from YAML front matter.

        Args:
            front_matter: Front matter dictionary
            file_path: Path to file (for fallback values)

        Returns:
            DocumentMetadata object
        """
        # Get title (fallback to filename)
        title = front_matter.get("title", file_path.stem)

        # Get timestamps
        created_at_str = front_matter.get("created_at")
        modified_at_str = front_matter.get("modified_at")

        # Parse or use file timestamps
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except (ValueError, TypeError):
                created_at = datetime.fromtimestamp(file_path.stat().st_ctime)
        else:
            created_at = datetime.fromtimestamp(file_path.stat().st_ctime)

        if modified_at_str:
            try:
                modified_at = datetime.fromisoformat(modified_at_str)
            except (ValueError, TypeError):
                modified_at = datetime.fromtimestamp(file_path.stat().st_mtime)
        else:
            modified_at = datetime.fromtimestamp(file_path.stat().st_mtime)

        # Get tags
        tags = front_matter.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        # Get other properties (exclude known metadata fields)
        properties = {
            k: v
            for k, v in front_matter.items()
            if k not in ("title", "created_at", "modified_at", "tags")
        }

        return DocumentMetadata(
            title=title,
            created_at=created_at,
            modified_at=modified_at,
            tags=tags,
            properties=properties,
        )

    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content.

        Args:
            content: Content to hash

        Returns:
            Hex string of hash
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
