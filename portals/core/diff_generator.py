"""Diff generation utilities for comparing document versions."""

from __future__ import annotations

import difflib
from dataclasses import dataclass


@dataclass
class DiffLine:
    """A single line in a diff."""

    type: str  # "common", "added", "removed"
    content: str
    line_number: int | None = None


class DiffGenerator:
    """Generate diffs between document versions.

    Provides unified diff and side-by-side comparison views.
    """

    def generate_unified_diff(
        self,
        local_content: str,
        remote_content: str,
        local_label: str = "LOCAL",
        remote_label: str = "REMOTE",
    ) -> str:
        """Generate unified diff between two versions.

        Args:
            local_content: Local file content
            remote_content: Remote document content
            local_label: Label for local version
            remote_label: Label for remote version

        Returns:
            Unified diff string
        """
        local_lines = local_content.splitlines(keepends=True)
        remote_lines = remote_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            local_lines,
            remote_lines,
            fromfile=local_label,
            tofile=remote_label,
            lineterm="",
        )

        return "".join(diff)

    def generate_side_by_side(
        self,
        local_content: str,
        remote_content: str,
    ) -> tuple[list[DiffLine], list[DiffLine]]:
        """Generate side-by-side diff.

        Args:
            local_content: Local file content
            remote_content: Remote document content

        Returns:
            Tuple of (local_diff_lines, remote_diff_lines)
        """
        local_lines = local_content.splitlines()
        remote_lines = remote_content.splitlines()

        # Use SequenceMatcher for detailed comparison
        matcher = difflib.SequenceMatcher(None, local_lines, remote_lines)

        local_diff: list[DiffLine] = []
        remote_diff: list[DiffLine] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                # Lines are the same
                for i, line in enumerate(local_lines[i1:i2]):
                    local_diff.append(
                        DiffLine(
                            type="common",
                            content=line,
                            line_number=i1 + i + 1,
                        )
                    )
                for j, line in enumerate(remote_lines[j1:j2]):
                    remote_diff.append(
                        DiffLine(
                            type="common",
                            content=line,
                            line_number=j1 + j + 1,
                        )
                    )

            elif tag == "delete":
                # Lines only in local
                for i, line in enumerate(local_lines[i1:i2]):
                    local_diff.append(
                        DiffLine(
                            type="removed",
                            content=line,
                            line_number=i1 + i + 1,
                        )
                    )

            elif tag == "insert":
                # Lines only in remote
                for j, line in enumerate(remote_lines[j1:j2]):
                    remote_diff.append(
                        DiffLine(
                            type="added",
                            content=line,
                            line_number=j1 + j + 1,
                        )
                    )

            elif tag == "replace":
                # Lines changed
                for i, line in enumerate(local_lines[i1:i2]):
                    local_diff.append(
                        DiffLine(
                            type="removed",
                            content=line,
                            line_number=i1 + i + 1,
                        )
                    )
                for j, line in enumerate(remote_lines[j1:j2]):
                    remote_diff.append(
                        DiffLine(
                            type="added",
                            content=line,
                            line_number=j1 + j + 1,
                        )
                    )

        return local_diff, remote_diff

    def generate_conflict_markers(
        self,
        local_content: str,
        remote_content: str,
        local_label: str = "LOCAL",
        remote_label: str = "REMOTE",
    ) -> str:
        """Generate content with conflict markers for manual editing.

        Args:
            local_content: Local file content
            remote_content: Remote document content
            local_label: Label for local version
            remote_label: Label for remote version

        Returns:
            Content with conflict markers
        """
        return (
            f"<<<<<<< {local_label}\n"
            f"{local_content}\n"
            f"=======\n"
            f"{remote_content}\n"
            f">>>>>>> {remote_label}\n"
        )

    def has_conflicts(self, local_content: str, remote_content: str) -> bool:
        """Check if two versions have differences.

        Args:
            local_content: Local file content
            remote_content: Remote document content

        Returns:
            True if contents differ
        """
        return local_content.strip() != remote_content.strip()

    def get_change_summary(
        self,
        local_content: str,
        remote_content: str,
    ) -> dict[str, int]:
        """Get summary of changes between versions.

        Args:
            local_content: Local file content
            remote_content: Remote document content

        Returns:
            Dictionary with change counts
        """
        local_lines = local_content.splitlines()
        remote_lines = remote_content.splitlines()

        matcher = difflib.SequenceMatcher(None, local_lines, remote_lines)

        additions = 0
        deletions = 0
        changes = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "delete":
                deletions += i2 - i1
            elif tag == "insert":
                additions += j2 - j1
            elif tag == "replace":
                changes += max(i2 - i1, j2 - j1)

        return {
            "additions": additions,
            "deletions": deletions,
            "changes": changes,
        }
