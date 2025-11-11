"""Hierarchy mapper for mapping directory structure to Notion pages."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from portals.adapters.notion.adapter import NotionAdapter
from portals.adapters.notion.hierarchy import NotionHierarchyManager
from portals.core.directory_scanner import FileInfo
from portals.core.models import Document, DocumentMetadata

logger = logging.getLogger(__name__)


@dataclass
class DirectoryNode:
    """A node in the directory tree."""

    path: Path
    relative_path: Path
    name: str
    children: list[DirectoryNode]
    files: list[FileInfo]
    notion_page_id: str | None = None


class HierarchyMapper:
    """Maps directory structure to Notion page hierarchy.

    Creates Notion pages for directories and maintains the hierarchical
    structure in Notion matching the local directory structure.
    """

    def __init__(
        self,
        base_path: str | Path,
        notion_adapter: NotionAdapter,
        hierarchy_manager: NotionHierarchyManager,
    ) -> None:
        """Initialize mapper.

        Args:
            base_path: Base directory path
            notion_adapter: Notion adapter for creating pages
            hierarchy_manager: Hierarchy manager for tracking mappings
        """
        self.base_path = Path(base_path).resolve()
        self.notion_adapter = notion_adapter
        self.hierarchy_manager = hierarchy_manager

    def build_directory_tree(self, files: list[FileInfo]) -> DirectoryNode:
        """Build directory tree from list of files.

        Args:
            files: List of file information objects

        Returns:
            Root directory node with children
        """
        # Create root node
        root = DirectoryNode(
            path=self.base_path,
            relative_path=Path("."),
            name=self.base_path.name,
            children=[],
            files=[],
        )

        # Group files by directory
        dir_to_files: dict[Path, list[FileInfo]] = {}
        for file_info in files:
            parent = file_info.relative_path.parent
            if parent not in dir_to_files:
                dir_to_files[parent] = []
            dir_to_files[parent].append(file_info)

        # Find all unique directories
        all_dirs: set[Path] = set()
        for file_info in files:
            # Add all parent directories
            for parent in file_info.relative_path.parents:
                if parent != Path("."):
                    all_dirs.add(parent)

        # Build directory nodes
        dir_nodes: dict[Path, DirectoryNode] = {
            Path("."): root,
        }

        # Create nodes for all directories (sorted to process parents first)
        for dir_path in sorted(all_dirs):
            node = DirectoryNode(
                path=self.base_path / dir_path,
                relative_path=dir_path,
                name=dir_path.name,
                children=[],
                files=dir_to_files.get(dir_path, []),
            )
            dir_nodes[dir_path] = node

        # Build parent-child relationships
        for dir_path, node in dir_nodes.items():
            if dir_path == Path("."):
                continue

            parent_path = dir_path.parent
            parent_node = dir_nodes.get(parent_path, root)
            parent_node.children.append(node)

        # Add files to root if any
        root.files = dir_to_files.get(Path("."), [])

        return root

    async def create_notion_hierarchy(
        self,
        tree: DirectoryNode,
        parent_page_id: str | None = None,
        dry_run: bool = False,
    ) -> int:
        """Create Notion pages for directory hierarchy.

        Args:
            tree: Directory tree root
            parent_page_id: Parent Notion page ID
            dry_run: If True, don't actually create pages

        Returns:
            Number of pages created
        """
        pages_created = 0

        # Use root page ID for top-level directories
        if parent_page_id is None:
            parent_page_id = self.hierarchy_manager.root_page_id

        # Process current directory (create page for it)
        if tree.relative_path != Path(".") and not dry_run:
            # Create page for this directory
            now = datetime.now()
            doc = Document(
                content=f"# {tree.name}\n\nThis page represents the `{tree.relative_path}` directory.",
                metadata=DocumentMetadata(
                    title=tree.name,
                    created_at=now,
                    modified_at=now,
                ),
            )

            notion_uri = await self.notion_adapter.create(
                uri="notion://",
                doc=doc,
                parent_id=parent_page_id,
            )

            # Extract page ID
            parsed = self.notion_adapter.parse_uri(notion_uri)
            tree.notion_page_id = parsed.identifier

            # Register in hierarchy manager
            self.hierarchy_manager.register_page(
                local_path=str(tree.relative_path),
                page_id=tree.notion_page_id,
                parent_id=parent_page_id,
            )

            pages_created += 1
            logger.info(f"Created folder page: {tree.relative_path}")

        # Recursively create pages for children directories
        for child in tree.children:
            child_parent_id = tree.notion_page_id or parent_page_id
            pages_created += await self.create_notion_hierarchy(
                child,
                parent_page_id=child_parent_id,
                dry_run=dry_run,
            )

        return pages_created

    def get_all_directories(self, tree: DirectoryNode) -> list[DirectoryNode]:
        """Get all directory nodes in tree.

        Args:
            tree: Root directory node

        Returns:
            Flat list of all directory nodes
        """
        directories = [tree]
        for child in tree.children:
            directories.extend(self.get_all_directories(child))
        return directories

    def get_directory_for_file(
        self,
        tree: DirectoryNode,
        file_path: Path,
    ) -> DirectoryNode | None:
        """Find directory node containing a file.

        Args:
            tree: Root directory node
            file_path: Relative path to file

        Returns:
            Directory node containing the file, or None
        """
        parent_path = file_path.parent

        if tree.relative_path == parent_path:
            return tree

        for child in tree.children:
            result = self.get_directory_for_file(child, file_path)
            if result:
                return result

        return None
