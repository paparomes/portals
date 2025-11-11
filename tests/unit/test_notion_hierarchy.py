"""Tests for NotionHierarchyManager."""

from __future__ import annotations

from pathlib import Path

from portals.adapters.notion.hierarchy import NotionHierarchyManager


class TestNotionHierarchyManager:
    """Tests for NotionHierarchyManager."""

    def test_initialization(self) -> None:
        """Test manager initialization."""
        manager = NotionHierarchyManager()
        assert manager.root_page_id is None
        assert manager.list_pages() == []

        manager_with_root = NotionHierarchyManager(root_page_id="root-123")
        assert manager_with_root.root_page_id == "root-123"

    def test_register_and_get_page_id(self) -> None:
        """Test registering and retrieving page IDs."""
        manager = NotionHierarchyManager()

        manager.register_page("docs/README.md", "page-123")
        assert manager.get_page_id("docs/README.md") == "page-123"

        # Test with Path object
        manager.register_page(Path("docs/guide.md"), "page-456")
        assert manager.get_page_id(Path("docs/guide.md")) == "page-456"

    def test_get_nonexistent_page_id(self) -> None:
        """Test getting page ID for unregistered path."""
        manager = NotionHierarchyManager()
        assert manager.get_page_id("docs/missing.md") is None

    def test_get_local_path(self) -> None:
        """Test reverse lookup from page ID to path."""
        manager = NotionHierarchyManager()
        manager.register_page("docs/README.md", "page-123")

        assert manager.get_local_path("page-123") == "docs/README.md"
        assert manager.get_local_path("page-nonexistent") is None

    def test_register_with_parent(self) -> None:
        """Test registering page with parent relationship."""
        manager = NotionHierarchyManager()

        manager.register_page("docs/README.md", "page-parent", parent_id=None)
        manager.register_page("docs/guide.md", "page-child", parent_id="page-parent")

        assert manager.get_parent_id("page-child") == "page-parent"
        assert manager.get_parent_id("page-parent") is None

    def test_get_parent_for_path_with_root(self) -> None:
        """Test getting parent for path at root level."""
        manager = NotionHierarchyManager(root_page_id="root-123")

        # File at root should return root_page_id
        parent = manager.get_parent_for_path("README.md")
        assert parent == "root-123"

    def test_get_parent_for_path_with_index(self) -> None:
        """Test getting parent for path with index page in parent directory."""
        manager = NotionHierarchyManager(root_page_id="root-123")

        # Register parent directory index
        manager.register_page("docs/index.md", "page-docs-index")

        # Child in docs/ should have docs/index.md as parent
        parent = manager.get_parent_for_path("docs/guide.md")
        assert parent == "page-docs-index"

    def test_get_parent_for_path_with_readme(self) -> None:
        """Test getting parent for path with README in parent directory."""
        manager = NotionHierarchyManager(root_page_id="root-123")

        # Register parent directory README
        manager.register_page("docs/README.md", "page-docs-readme")

        # Child in docs/ should have docs/README.md as parent
        parent = manager.get_parent_for_path("docs/guide.md")
        assert parent == "page-docs-readme"

    def test_get_parent_for_path_recursive(self) -> None:
        """Test getting parent for deeply nested path."""
        manager = NotionHierarchyManager(root_page_id="root-123")

        # Register index at top level
        manager.register_page("docs/index.md", "page-docs")

        # Nested file should find parent recursively
        parent = manager.get_parent_for_path("docs/advanced/concepts.md")
        assert parent == "page-docs"

    def test_get_parent_for_path_no_match(self) -> None:
        """Test getting parent when no parent pages registered."""
        manager = NotionHierarchyManager(root_page_id="root-123")

        # No registered pages, should return root
        parent = manager.get_parent_for_path("docs/guide.md")
        assert parent == "root-123"

    def test_unregister_page(self) -> None:
        """Test unregistering a page."""
        manager = NotionHierarchyManager()
        manager.register_page("docs/README.md", "page-123", parent_id="parent-123")

        assert manager.has_page("docs/README.md")

        manager.unregister_page("docs/README.md")

        assert not manager.has_page("docs/README.md")
        assert manager.get_page_id("docs/README.md") is None
        assert manager.get_local_path("page-123") is None
        assert manager.get_parent_id("page-123") is None

    def test_unregister_nonexistent_page(self) -> None:
        """Test unregistering a page that doesn't exist."""
        manager = NotionHierarchyManager()
        # Should not raise error
        manager.unregister_page("docs/missing.md")

    def test_list_pages(self) -> None:
        """Test listing all registered pages."""
        manager = NotionHierarchyManager()

        manager.register_page("docs/README.md", "page-1")
        manager.register_page("docs/guide.md", "page-2")

        pages = manager.list_pages()
        assert len(pages) == 2
        assert ("docs/README.md", "page-1") in pages
        assert ("docs/guide.md", "page-2") in pages

    def test_get_children(self) -> None:
        """Test getting child pages."""
        manager = NotionHierarchyManager()

        manager.register_page("docs/README.md", "page-parent")
        manager.register_page("docs/guide1.md", "page-child1", parent_id="page-parent")
        manager.register_page("docs/guide2.md", "page-child2", parent_id="page-parent")
        manager.register_page("docs/other.md", "page-other", parent_id="different-parent")

        children = manager.get_children("page-parent")
        assert len(children) == 2
        assert "page-child1" in children
        assert "page-child2" in children
        assert "page-other" not in children

    def test_get_children_no_children(self) -> None:
        """Test getting children when page has no children."""
        manager = NotionHierarchyManager()
        manager.register_page("docs/README.md", "page-123")

        children = manager.get_children("page-123")
        assert children == []

    def test_to_dict(self) -> None:
        """Test exporting hierarchy to dictionary."""
        manager = NotionHierarchyManager(root_page_id="root-123")
        manager.register_page("docs/README.md", "page-1", parent_id="root-123")
        manager.register_page("docs/guide.md", "page-2", parent_id="page-1")

        data = manager.to_dict()

        assert data["root_page_id"] == "root-123"
        assert "docs/README.md" in data["path_to_page_id"]
        assert data["path_to_page_id"]["docs/README.md"] == "page-1"
        assert data["page_id_to_parent"]["page-1"] == "root-123"
        assert data["page_id_to_parent"]["page-2"] == "page-1"

    def test_from_dict(self) -> None:
        """Test creating hierarchy from dictionary."""
        data = {
            "root_page_id": "root-123",
            "path_to_page_id": {
                "docs/README.md": "page-1",
                "docs/guide.md": "page-2",
            },
            "page_id_to_parent": {
                "page-1": "root-123",
                "page-2": "page-1",
            },
        }

        manager = NotionHierarchyManager.from_dict(data)

        assert manager.root_page_id == "root-123"
        assert manager.get_page_id("docs/README.md") == "page-1"
        assert manager.get_page_id("docs/guide.md") == "page-2"
        assert manager.get_local_path("page-1") == "docs/README.md"
        assert manager.get_parent_id("page-1") == "root-123"
        assert manager.get_parent_id("page-2") == "page-1"

    def test_from_dict_empty(self) -> None:
        """Test creating hierarchy from empty dictionary."""
        manager = NotionHierarchyManager.from_dict({})

        assert manager.root_page_id is None
        assert manager.list_pages() == []

    def test_clear(self) -> None:
        """Test clearing all hierarchy mappings."""
        manager = NotionHierarchyManager()
        manager.register_page("docs/README.md", "page-1")
        manager.register_page("docs/guide.md", "page-2", parent_id="page-1")

        assert len(manager.list_pages()) == 2

        manager.clear()

        assert manager.list_pages() == []
        assert manager.get_page_id("docs/README.md") is None
        assert manager.get_local_path("page-1") is None

    def test_has_page(self) -> None:
        """Test checking if page is registered."""
        manager = NotionHierarchyManager()

        assert not manager.has_page("docs/README.md")

        manager.register_page("docs/README.md", "page-123")

        assert manager.has_page("docs/README.md")
        assert manager.has_page(Path("docs/README.md"))
        assert not manager.has_page("docs/guide.md")

    def test_get_depth_root_level(self) -> None:
        """Test getting depth for root-level page."""
        manager = NotionHierarchyManager(root_page_id="root-123")
        manager.register_page("README.md", "page-1", parent_id="root-123")

        assert manager.get_depth("page-1") == 0

    def test_get_depth_nested(self) -> None:
        """Test getting depth for nested pages."""
        manager = NotionHierarchyManager(root_page_id="root-123")
        manager.register_page("docs/index.md", "page-1", parent_id="root-123")
        manager.register_page("docs/guide.md", "page-2", parent_id="page-1")
        manager.register_page("docs/guide/advanced.md", "page-3", parent_id="page-2")

        assert manager.get_depth("page-1") == 0  # Direct child of root
        assert manager.get_depth("page-2") == 1  # Child of page-1
        assert manager.get_depth("page-3") == 2  # Grandchild of page-1

    def test_get_depth_no_parent(self) -> None:
        """Test getting depth for page with no parent."""
        manager = NotionHierarchyManager()
        manager.register_page("README.md", "page-1")

        assert manager.get_depth("page-1") == 0

    def test_path_normalization(self) -> None:
        """Test that paths are normalized consistently."""
        manager = NotionHierarchyManager()

        # Register with string
        manager.register_page("docs/README.md", "page-123")

        # Should find with Path object
        assert manager.get_page_id(Path("docs/README.md")) == "page-123"
        assert manager.has_page("docs/README.md")
        assert manager.has_page(Path("docs/README.md"))

    def test_roundtrip_serialization(self) -> None:
        """Test complete roundtrip of serialization and deserialization."""
        original = NotionHierarchyManager(root_page_id="root-123")
        original.register_page("docs/README.md", "page-1", parent_id="root-123")
        original.register_page("docs/guide.md", "page-2", parent_id="page-1")
        original.register_page("docs/advanced/concepts.md", "page-3", parent_id="page-2")

        # Export and reimport
        data = original.to_dict()
        restored = NotionHierarchyManager.from_dict(data)

        # Verify all data preserved
        assert restored.root_page_id == original.root_page_id
        assert restored.list_pages() == original.list_pages()
        assert restored.get_parent_id("page-1") == original.get_parent_id("page-1")
        assert restored.get_parent_id("page-2") == original.get_parent_id("page-2")
        assert restored.get_parent_id("page-3") == original.get_parent_id("page-3")
        assert restored.get_children("page-1") == original.get_children("page-1")

    def test_multiple_files_same_directory(self) -> None:
        """Test handling multiple files in the same directory."""
        manager = NotionHierarchyManager(root_page_id="root-123")

        manager.register_page("docs/file1.md", "page-1")
        manager.register_page("docs/file2.md", "page-2")
        manager.register_page("docs/file3.md", "page-3")

        # All should be registered
        assert manager.has_page("docs/file1.md")
        assert manager.has_page("docs/file2.md")
        assert manager.has_page("docs/file3.md")

        # All should have different IDs
        ids = [
            manager.get_page_id("docs/file1.md"),
            manager.get_page_id("docs/file2.md"),
            manager.get_page_id("docs/file3.md"),
        ]
        assert len(set(ids)) == 3  # All unique

    def test_overwrite_registration(self) -> None:
        """Test that re-registering a path updates the mapping."""
        manager = NotionHierarchyManager()

        manager.register_page("docs/README.md", "page-old")
        assert manager.get_page_id("docs/README.md") == "page-old"

        # Re-register with new ID
        manager.register_page("docs/README.md", "page-new")
        assert manager.get_page_id("docs/README.md") == "page-new"

        # Old ID should not have reverse mapping
        assert manager.get_local_path("page-old") is None
