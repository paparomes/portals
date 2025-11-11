"""Notion hierarchy manager for mapping directory structures to page relationships."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class NotionHierarchyManager:
    """Manages mapping between local directory structure and Notion page hierarchy.

    Tracks relationships between local file paths and Notion page IDs,
    maintaining the parent-child structure needed for Notion's page organization.
    """

    def __init__(self, root_page_id: str | None = None) -> None:
        """Initialize hierarchy manager.

        Args:
            root_page_id: Optional root page ID for top-level pages
        """
        self.root_page_id = root_page_id
        self._path_to_page_id: dict[str, str] = {}
        self._page_id_to_path: dict[str, str] = {}
        self._page_id_to_parent: dict[str, str] = {}

    def register_page(
        self,
        local_path: str | Path,
        page_id: str,
        parent_id: str | None = None,
    ) -> None:
        """Register a mapping between local path and Notion page.

        Args:
            local_path: Local file path
            page_id: Notion page ID
            parent_id: Optional parent page ID
        """
        path_str = str(Path(local_path))
        self._path_to_page_id[path_str] = page_id
        self._page_id_to_path[page_id] = path_str

        if parent_id:
            self._page_id_to_parent[page_id] = parent_id

    def get_page_id(self, local_path: str | Path) -> str | None:
        """Get Notion page ID for a local path.

        Args:
            local_path: Local file path

        Returns:
            Notion page ID if registered, None otherwise
        """
        return self._path_to_page_id.get(str(Path(local_path)))

    def get_local_path(self, page_id: str) -> str | None:
        """Get local path for a Notion page ID.

        Args:
            page_id: Notion page ID

        Returns:
            Local path if registered, None otherwise
        """
        return self._page_id_to_path.get(page_id)

    def get_parent_id(self, page_id: str) -> str | None:
        """Get parent page ID for a given page.

        Args:
            page_id: Notion page ID

        Returns:
            Parent page ID if exists, None otherwise
        """
        return self._page_id_to_parent.get(page_id)

    def get_parent_for_path(self, local_path: str | Path) -> str | None:
        """Get parent page ID for a local path based on directory structure.

        Looks up the parent directory's page ID to maintain hierarchy.

        Args:
            local_path: Local file path

        Returns:
            Parent page ID if parent directory is registered, root_page_id if at top level,
            None if no parent can be determined
        """
        path = Path(local_path)
        parent_dir = path.parent

        # If we're at the root (parent is '.'), return root_page_id
        if parent_dir == Path("."):
            return self.root_page_id

        # Look for parent directory's index page or any page in that directory
        # First try to find an index/README in the parent directory
        for index_name in ["index.md", "README.md", "readme.md"]:
            index_path = parent_dir / index_name
            parent_id = self.get_page_id(index_path)
            if parent_id:
                return parent_id

        # If no index page, try to find any registered page in parent directory
        for registered_path in self._path_to_page_id:
            if Path(registered_path).parent == parent_dir:
                return self._path_to_page_id[registered_path]

        # Recursively check grandparent
        if parent_dir != Path("."):
            return self.get_parent_for_path(parent_dir)

        return self.root_page_id

    def unregister_page(self, local_path: str | Path) -> None:
        """Unregister a page mapping.

        Args:
            local_path: Local file path to unregister
        """
        path_str = str(Path(local_path))
        page_id = self._path_to_page_id.pop(path_str, None)

        if page_id:
            self._page_id_to_path.pop(page_id, None)
            self._page_id_to_parent.pop(page_id, None)

    def list_pages(self) -> list[tuple[str, str]]:
        """List all registered page mappings.

        Returns:
            List of (local_path, page_id) tuples
        """
        return list(self._path_to_page_id.items())

    def get_children(self, page_id: str) -> list[str]:
        """Get child page IDs for a given parent.

        Args:
            page_id: Parent page ID

        Returns:
            List of child page IDs
        """
        return [
            child_id
            for child_id, parent_id in self._page_id_to_parent.items()
            if parent_id == page_id
        ]

    def to_dict(self) -> dict[str, Any]:
        """Export hierarchy data to dictionary.

        Returns:
            Dictionary representation of hierarchy mappings
        """
        return {
            "root_page_id": self.root_page_id,
            "path_to_page_id": self._path_to_page_id,
            "page_id_to_parent": self._page_id_to_parent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotionHierarchyManager:
        """Create hierarchy manager from dictionary.

        Args:
            data: Dictionary with hierarchy data

        Returns:
            NotionHierarchyManager instance
        """
        manager = cls(root_page_id=data.get("root_page_id"))
        manager._path_to_page_id = data.get("path_to_page_id", {})
        manager._page_id_to_parent = data.get("page_id_to_parent", {})

        # Rebuild page_id_to_path from path_to_page_id
        manager._page_id_to_path = {
            page_id: path for path, page_id in manager._path_to_page_id.items()
        }

        return manager

    def clear(self) -> None:
        """Clear all hierarchy mappings."""
        self._path_to_page_id.clear()
        self._page_id_to_path.clear()
        self._page_id_to_parent.clear()

    def has_page(self, local_path: str | Path) -> bool:
        """Check if a local path has a registered page.

        Args:
            local_path: Local file path

        Returns:
            True if path is registered, False otherwise
        """
        return str(Path(local_path)) in self._path_to_page_id

    def get_depth(self, page_id: str) -> int:
        """Get the depth of a page in the hierarchy.

        Args:
            page_id: Notion page ID

        Returns:
            Depth (0 for root-level pages, increases with nesting)
        """
        depth = 0
        current_id = page_id

        while True:
            parent_id = self.get_parent_id(current_id)
            if not parent_id or parent_id == self.root_page_id:
                break
            depth += 1
            current_id = parent_id

            # Prevent infinite loops
            if depth > 100:
                break

        return depth
