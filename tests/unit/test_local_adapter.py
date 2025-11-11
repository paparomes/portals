"""Tests for LocalFileAdapter."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from portals.adapters.local import LocalFileAdapter
from portals.core.exceptions import LocalFileError
from portals.core.models import Document, DocumentMetadata


@pytest.fixture
def adapter(tmp_path: Path) -> LocalFileAdapter:
    """Create LocalFileAdapter with temporary directory."""
    return LocalFileAdapter(base_path=str(tmp_path))


@pytest.fixture
def sample_doc() -> Document:
    """Create sample document for testing."""
    return Document(
        content="# Test Document\n\nThis is a test.",
        metadata=DocumentMetadata(
            title="Test Document",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            modified_at=datetime(2024, 1, 2, 12, 0, 0),
            tags=["test", "sample"],
            properties={"author": "Test Author"},
        ),
    )


class TestLocalFileAdapter:
    """Tests for LocalFileAdapter."""

    async def test_write_and_read(
        self, adapter: LocalFileAdapter, sample_doc: Document, tmp_path: Path
    ) -> None:
        """Test writing and reading a document."""
        file_path = tmp_path / "test.md"

        # Write document
        await adapter.write(str(file_path), sample_doc)

        # Verify file exists
        assert file_path.exists()

        # Read document back
        doc = await adapter.read(str(file_path))

        # Verify content
        assert doc.content == sample_doc.content
        assert doc.metadata.title == sample_doc.metadata.title
        assert doc.metadata.tags == sample_doc.metadata.tags
        assert doc.metadata.properties == sample_doc.metadata.properties
        assert doc.content_hash is not None

    async def test_read_file_with_front_matter(
        self, adapter: LocalFileAdapter, tmp_path: Path
    ) -> None:
        """Test reading file with YAML front matter."""
        file_path = tmp_path / "with_frontmatter.md"

        # Create file with front matter
        content = """---
title: My Document
tags:
  - tag1
  - tag2
author: John Doe
---
# Content

This is the actual content."""

        file_path.write_text(content, encoding="utf-8")

        # Read document
        doc = await adapter.read(str(file_path))

        # Verify metadata
        assert doc.metadata.title == "My Document"
        assert doc.metadata.tags == ["tag1", "tag2"]
        assert doc.metadata.properties["author"] == "John Doe"

        # Verify content (without front matter)
        assert doc.content.strip().startswith("# Content")
        assert "This is the actual content" in doc.content

    async def test_read_file_without_front_matter(
        self, adapter: LocalFileAdapter, tmp_path: Path
    ) -> None:
        """Test reading file without front matter."""
        file_path = tmp_path / "no_frontmatter.md"

        # Create file without front matter
        content = "# Simple Document\n\nJust content, no metadata."
        file_path.write_text(content, encoding="utf-8")

        # Read document
        doc = await adapter.read(str(file_path))

        # Verify title falls back to filename
        assert doc.metadata.title == "no_frontmatter"

        # Verify content
        assert doc.content == content

        # Verify timestamps exist (from file stats)
        assert doc.metadata.created_at is not None
        assert doc.metadata.modified_at is not None

    async def test_read_nonexistent_file(self, adapter: LocalFileAdapter, tmp_path: Path) -> None:
        """Test reading a file that doesn't exist."""
        file_path = tmp_path / "nonexistent.md"

        with pytest.raises(LocalFileError, match="File not found"):
            await adapter.read(str(file_path))

    async def test_write_creates_parent_directories(
        self, adapter: LocalFileAdapter, sample_doc: Document, tmp_path: Path
    ) -> None:
        """Test that writing creates parent directories."""
        file_path = tmp_path / "nested" / "dirs" / "test.md"

        # Write document (should create nested/dirs/)
        await adapter.write(str(file_path), sample_doc)

        # Verify file and directories exist
        assert file_path.exists()
        assert file_path.parent.exists()

    async def test_get_metadata(
        self, adapter: LocalFileAdapter, sample_doc: Document, tmp_path: Path
    ) -> None:
        """Test getting metadata without reading full content."""
        file_path = tmp_path / "test.md"

        # Write document
        await adapter.write(str(file_path), sample_doc)

        # Get metadata
        metadata = await adapter.get_metadata(str(file_path))

        # Verify metadata
        assert metadata.uri == str(file_path)
        assert metadata.exists is True
        assert metadata.content_hash != ""
        assert metadata.last_modified != ""

    async def test_get_metadata_nonexistent(
        self, adapter: LocalFileAdapter, tmp_path: Path
    ) -> None:
        """Test getting metadata for nonexistent file."""
        file_path = tmp_path / "nonexistent.md"

        metadata = await adapter.get_metadata(str(file_path))

        assert metadata.exists is False
        assert metadata.content_hash == ""

    async def test_exists(
        self, adapter: LocalFileAdapter, sample_doc: Document, tmp_path: Path
    ) -> None:
        """Test checking file existence."""
        file_path = tmp_path / "test.md"

        # File doesn't exist yet
        assert await adapter.exists(str(file_path)) is False

        # Write file
        await adapter.write(str(file_path), sample_doc)

        # File now exists
        assert await adapter.exists(str(file_path)) is True

    async def test_parse_uri_file_protocol(self, adapter: LocalFileAdapter) -> None:
        """Test parsing file:// URI."""
        uri = "file:///path/to/file.md"

        parsed = adapter.parse_uri(uri)

        assert parsed.platform == "file"
        assert parsed.identifier == "/path/to/file.md"
        assert parsed.raw_uri == uri

    async def test_parse_uri_absolute_path(self, adapter: LocalFileAdapter) -> None:
        """Test parsing absolute path without file:// prefix."""
        uri = "/path/to/file.md"

        parsed = adapter.parse_uri(uri)

        assert parsed.platform == "file"
        assert "/path/to/file.md" in parsed.identifier

    async def test_create(
        self, adapter: LocalFileAdapter, sample_doc: Document, tmp_path: Path
    ) -> None:
        """Test creating a new file."""
        file_path = tmp_path / "new.md"

        # Create file
        uri = await adapter.create(str(file_path), sample_doc)

        # Verify file exists
        assert file_path.exists()
        assert "file://" in uri

        # Verify can't create again
        with pytest.raises(LocalFileError, match="already exists"):
            await adapter.create(str(file_path), sample_doc)

    async def test_delete(
        self, adapter: LocalFileAdapter, sample_doc: Document, tmp_path: Path
    ) -> None:
        """Test deleting a file."""
        file_path = tmp_path / "to_delete.md"

        # Create file
        await adapter.write(str(file_path), sample_doc)
        assert file_path.exists()

        # Delete file
        await adapter.delete(str(file_path))
        assert not file_path.exists()

        # Verify can't delete again
        with pytest.raises(LocalFileError, match="File not found"):
            await adapter.delete(str(file_path))

    async def test_content_hash_consistency(
        self, adapter: LocalFileAdapter, sample_doc: Document, tmp_path: Path
    ) -> None:
        """Test that content hash is consistent."""
        file_path = tmp_path / "test.md"

        # Write document
        await adapter.write(str(file_path), sample_doc)

        # Read twice
        doc1 = await adapter.read(str(file_path))
        doc2 = await adapter.read(str(file_path))

        # Hashes should match
        assert doc1.content_hash == doc2.content_hash

    async def test_content_hash_changes_with_content(
        self, adapter: LocalFileAdapter, sample_doc: Document, tmp_path: Path
    ) -> None:
        """Test that content hash changes when content changes."""
        file_path = tmp_path / "test.md"

        # Write initial document
        await adapter.write(str(file_path), sample_doc)
        doc1 = await adapter.read(str(file_path))

        # Modify content
        sample_doc.content = "# Modified\n\nDifferent content."
        await adapter.write(str(file_path), sample_doc)
        doc2 = await adapter.read(str(file_path))

        # Hashes should differ
        assert doc1.content_hash != doc2.content_hash

    async def test_relative_path_resolution(
        self, adapter: LocalFileAdapter, sample_doc: Document, tmp_path: Path
    ) -> None:
        """Test that relative paths are resolved against base_path."""
        # Use relative path
        await adapter.write("test.md", sample_doc)

        # File should be in base_path (tmp_path)
        file_path = tmp_path / "test.md"
        assert file_path.exists()

        # Should be able to read with relative path
        doc = await adapter.read("test.md")
        assert doc.content == sample_doc.content

    async def test_tags_as_string(self, adapter: LocalFileAdapter, tmp_path: Path) -> None:
        """Test handling tags as a string instead of list."""
        file_path = tmp_path / "test.md"

        content = """---
title: Test
tags: single-tag
---
Content"""

        file_path.write_text(content, encoding="utf-8")

        doc = await adapter.read(str(file_path))

        # Tags should be converted to list
        assert doc.metadata.tags == ["single-tag"]
