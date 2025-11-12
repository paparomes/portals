"""Notion poller for detecting remote changes."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from notion_client import AsyncClient

from portals.core.models import SyncPair
from portals.utils.logging import get_logger

logger = get_logger(__name__)


class RemoteChange:
    """Represents a remote change detected in Notion."""

    def __init__(
        self,
        pair: SyncPair,
        last_edited_time: datetime,
    ) -> None:
        """Initialize remote change.

        Args:
            pair: Sync pair that changed
            last_edited_time: Time of last edit in Notion
        """
        self.pair = pair
        self.last_edited_time = last_edited_time

    def __repr__(self) -> str:
        return (
            f"RemoteChange(pair={self.pair.local_path}, "
            f"time={self.last_edited_time})"
        )


class NotionPoller:
    """Polls Notion for remote changes."""

    def __init__(
        self,
        notion_client: AsyncClient,
        sync_pairs: list[SyncPair],
        poll_interval_seconds: float = 30.0,
    ) -> None:
        """Initialize Notion poller.

        Args:
            notion_client: Notion API client
            sync_pairs: List of sync pairs to monitor
            poll_interval_seconds: Seconds between polls
        """
        self.notion_client = notion_client
        self.sync_pairs = sync_pairs
        self.poll_interval_seconds = poll_interval_seconds
        self.is_running = False
        self.poll_task: asyncio.Task[None] | None = None
        self.last_checked: dict[str, datetime] = {}

        logger.info(
            "notion_poller_initialized",
            pairs_count=len(sync_pairs),
            interval=poll_interval_seconds,
        )

    async def check_for_changes(self) -> list[RemoteChange]:
        """Check for changes in Notion.

        Returns:
            List of detected remote changes
        """
        changes: list[RemoteChange] = []

        for pair in self.sync_pairs:
            try:
                # Extract page ID from remote URI (notion://page-id)
                page_id = pair.remote_uri.replace("notion://", "")

                # Get page metadata from Notion
                page = await self.notion_client.pages.retrieve(page_id)

                # Parse last_edited_time
                last_edited_str = page.get("last_edited_time")
                if not last_edited_str:
                    logger.warning(
                        "no_last_edited_time",
                        page_id=page_id,
                        pair=str(pair.local_path),
                    )
                    continue

                last_edited_time = datetime.fromisoformat(
                    last_edited_str.replace("Z", "+00:00")
                )

                # Check if changed since last check
                last_check = self.last_checked.get(page_id)
                if last_check and last_edited_time <= last_check:
                    # No change
                    continue

                # Check if changed since last sync
                if pair.state and pair.state.last_synced_hash:
                    # Compare with pair's last sync time
                    if last_edited_time <= pair.state.last_sync:
                        # No change since last sync
                        continue

                # Change detected
                logger.info(
                    "remote_change_detected",
                    page_id=page_id,
                    pair=str(pair.local_path),
                    last_edited=last_edited_str,
                )

                changes.append(RemoteChange(pair, last_edited_time))
                self.last_checked[page_id] = last_edited_time

            except Exception as e:
                logger.error(
                    "error_checking_notion_page",
                    page_id=page_id,
                    pair=str(pair.local_path),
                    error=str(e),
                )
                continue

        return changes

    async def _poll_loop(self, on_change_callback: Any) -> None:
        """Main polling loop.

        Args:
            on_change_callback: Callback for detected changes
        """
        while self.is_running:
            try:
                changes = await self.check_for_changes()

                # Call callback for each change
                for change in changes:
                    try:
                        await on_change_callback(change)
                    except Exception as e:
                        logger.error(
                            "error_in_change_callback",
                            pair=str(change.pair.local_path),
                            error=str(e),
                        )

            except Exception as e:
                logger.error("error_in_poll_loop", error=str(e))

            # Wait for next poll interval
            await asyncio.sleep(self.poll_interval_seconds)

    def start(self, on_change_callback: Any) -> None:
        """Start polling for changes.

        Args:
            on_change_callback: Callback for detected changes
        """
        if self.is_running:
            logger.warning("notion_poller_already_running")
            return

        self.is_running = True
        self.poll_task = asyncio.create_task(self._poll_loop(on_change_callback))

        logger.info("notion_poller_started")

    async def stop(self) -> None:
        """Stop polling for changes."""
        if not self.is_running:
            logger.warning("notion_poller_not_running")
            return

        self.is_running = False

        if self.poll_task:
            self.poll_task.cancel()
            try:
                await self.poll_task
            except asyncio.CancelledError:
                pass

        logger.info("notion_poller_stopped")

    async def __aenter__(self) -> NotionPoller:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.stop()
