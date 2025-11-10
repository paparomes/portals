"""Custom exceptions for Portals."""


class PortalsError(Exception):
    """Base exception for all Portals errors."""

    pass


class ConfigError(PortalsError):
    """Configuration errors."""

    pass


class SyncError(PortalsError):
    """Sync operation errors."""

    pass


class ConflictError(SyncError):
    """Conflict detected during sync."""

    def __init__(self, message: str, local_hash: str, remote_hash: str) -> None:
        """Initialize conflict error.

        Args:
            message: Error message
            local_hash: Hash of local content
            remote_hash: Hash of remote content
        """
        super().__init__(message)
        self.local_hash = local_hash
        self.remote_hash = remote_hash


class AdapterError(PortalsError):
    """Platform adapter errors."""

    pass


class NotionError(AdapterError):
    """Notion-specific errors."""

    pass


class GoogleDocsError(AdapterError):
    """Google Docs-specific errors."""

    pass


class ObsidianError(AdapterError):
    """Obsidian-specific errors."""

    pass


class LocalFileError(AdapterError):
    """Local file system errors."""

    pass


class MetadataError(PortalsError):
    """Metadata store errors."""

    pass


class ValidationError(PortalsError):
    """Validation errors."""

    pass
