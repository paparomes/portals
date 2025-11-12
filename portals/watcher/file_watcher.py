"""File system watcher for detecting local changes."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import structlog
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from portals.utils.logging import get_logger

logger = get_logger(__name__)


class ChangeEvent:
    """Represents a file change event."""

    def __init__(
        self,
        path: Path,
        event_type: str,
        timestamp: float,
    ) -> None:
        """Initialize change event.

        Args:
            path: Path to changed file
            event_type: Type of event (created, modified, deleted, moved)
            timestamp: Time of event
        """
        self.path = path
        self.event_type = event_type
        self.timestamp = timestamp

    def __repr__(self) -> str:
        return f"ChangeEvent(path={self.path}, type={self.event_type}, time={self.timestamp})"


class FileWatcherHandler(FileSystemEventHandler):
    """Handler for watchdog file system events."""

    def __init__(
        self,
        base_path: Path,
        on_change_callback: Any,
        debounce_seconds: float = 2.0,
    ) -> None:
        """Initialize handler.

        Args:
            base_path: Base directory being watched
            on_change_callback: Callback function for changes
            debounce_seconds: Seconds to wait before processing change
        """
        self.base_path = base_path
        self.on_change_callback = on_change_callback
        self.debounce_seconds = debounce_seconds
        self.pending_changes: dict[Path, ChangeEvent] = {}
        self.last_change_time: dict[Path, float] = {}

    def _should_process(self, event: FileSystemEvent) -> bool:
        """Check if event should be processed.

        Args:
            event: File system event

        Returns:
            True if event should be processed
        """
        # Ignore directories
        if event.is_directory:
            return False

        path = Path(event.src_path)

        # Only process .md files
        if path.suffix != ".md":
            return False

        # Ignore hidden files
        if any(part.startswith(".") for part in path.parts):
            return False

        # Ignore .docsync directory
        if ".docsync" in path.parts:
            return False

        # Ignore git directory
        if ".git" in path.parts:
            return False

        return True

    def _debounce_change(self, path: Path, event_type: str) -> bool:
        """Check if change should be debounced.

        Args:
            path: Path to file
            event_type: Type of event

        Returns:
            True if change should be processed now, False if still debouncing
        """
        now = time.time()
        last_change = self.last_change_time.get(path, 0)

        # If enough time has passed since last change
        if now - last_change >= self.debounce_seconds:
            self.last_change_time[path] = now
            return True

        # Still within debounce window - update pending change
        self.pending_changes[path] = ChangeEvent(path, event_type, now)
        return False

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file created event.

        Args:
            event: File system event
        """
        if not self._should_process(event):
            return

        path = Path(event.src_path).relative_to(self.base_path)
        logger.debug("file_created", path=str(path))

        if self._debounce_change(path, "created"):
            change_event = ChangeEvent(path, "created", time.time())
            self.on_change_callback(change_event)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modified event.

        Args:
            event: File system event
        """
        if not self._should_process(event):
            return

        path = Path(event.src_path).relative_to(self.base_path)
        logger.debug("file_modified", path=str(path))

        if self._debounce_change(path, "modified"):
            change_event = ChangeEvent(path, "modified", time.time())
            self.on_change_callback(change_event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deleted event.

        Args:
            event: File system event
        """
        if not self._should_process(event):
            return

        path = Path(event.src_path).relative_to(self.base_path)
        logger.debug("file_deleted", path=str(path))

        # No debouncing for deletes
        change_event = ChangeEvent(path, "deleted", time.time())
        self.on_change_callback(change_event)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file moved event.

        Args:
            event: File system event
        """
        if not self._should_process(event):
            return

        path = Path(event.src_path).relative_to(self.base_path)
        logger.debug("file_moved", path=str(path))

        # Treat moves as delete + create
        delete_event = ChangeEvent(path, "deleted", time.time())
        self.on_change_callback(delete_event)


class FileWatcher:
    """Watches local file system for changes."""

    def __init__(
        self,
        base_path: Path,
        on_change_callback: Any,
        debounce_seconds: float = 2.0,
    ) -> None:
        """Initialize file watcher.

        Args:
            base_path: Directory to watch
            on_change_callback: Callback function when changes detected
            debounce_seconds: Seconds to wait before processing change
        """
        self.base_path = base_path
        self.on_change_callback = on_change_callback
        self.debounce_seconds = debounce_seconds
        self.observer: Observer | None = None
        self.handler: FileWatcherHandler | None = None
        self.is_running = False

        logger.info("file_watcher_initialized", base_path=str(base_path))

    def start(self) -> None:
        """Start watching for file changes."""
        if self.is_running:
            logger.warning("file_watcher_already_running")
            return

        self.handler = FileWatcherHandler(
            base_path=self.base_path,
            on_change_callback=self.on_change_callback,
            debounce_seconds=self.debounce_seconds,
        )

        self.observer = Observer()
        self.observer.schedule(
            self.handler,
            str(self.base_path),
            recursive=True,
        )
        self.observer.start()
        self.is_running = True

        logger.info("file_watcher_started", base_path=str(self.base_path))

    def stop(self) -> None:
        """Stop watching for file changes."""
        if not self.is_running or not self.observer:
            logger.warning("file_watcher_not_running")
            return

        self.observer.stop()
        self.observer.join(timeout=5.0)
        self.is_running = False

        logger.info("file_watcher_stopped")

    def __enter__(self) -> FileWatcher:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.stop()
