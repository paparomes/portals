"""Tests for NotionPoller."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from portals.core.models import SyncPair
from portals.watcher.notion_poller import NotionPoller, RemoteChange


@pytest.fixture
def mock_notion_client():
    """Mock Notion async client."""
    client = AsyncMock()
    return client


@pytest.fixture
def sample_sync_pairs():
    """Create sample sync pairs."""
    from portals.core.models import SyncPairState, SyncDirection, ConflictResolution

    return [
        SyncPair(
            id="pair1",
            local_path="doc1.md",
            remote_uri="notion://page-id-1",
            remote_platform="notion",
            created_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            sync_direction=SyncDirection.BIDIRECTIONAL,
            conflict_resolution=ConflictResolution.MANUAL,
            state=SyncPairState(
                local_hash="hash1-local",
                remote_hash="hash1-remote",
                last_synced_hash="hash1",
                last_sync=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            ),
        ),
        SyncPair(
            id="pair2",
            local_path="doc2.md",
            remote_uri="notion://page-id-2",
            remote_platform="notion",
            created_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            sync_direction=SyncDirection.BIDIRECTIONAL,
            conflict_resolution=ConflictResolution.MANUAL,
            state=SyncPairState(
                local_hash="hash2-local",
                remote_hash="hash2-remote",
                last_synced_hash="hash2",
                last_sync=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            ),
        ),
    ]


@pytest.fixture
def notion_poller(mock_notion_client, sample_sync_pairs):
    """Create NotionPoller instance."""
    return NotionPoller(
        notion_client=mock_notion_client,
        sync_pairs=sample_sync_pairs,
        poll_interval_seconds=0.1,  # Short interval for testing
    )


class TestNotionPoller:
    """Tests for NotionPoller."""

    def test_initialization(self, mock_notion_client, sample_sync_pairs):
        """Test NotionPoller initialization."""
        poller = NotionPoller(
            notion_client=mock_notion_client,
            sync_pairs=sample_sync_pairs,
            poll_interval_seconds=30.0,
        )

        assert poller.notion_client == mock_notion_client
        assert poller.sync_pairs == sample_sync_pairs
        assert poller.poll_interval_seconds == 30.0
        assert poller.is_running is False
        assert len(poller.last_checked) == 0

    @pytest.mark.asyncio
    async def test_check_for_changes_no_changes(
        self, notion_poller, mock_notion_client
    ):
        """Test checking for changes when there are none."""
        # Mock Notion API to return same timestamp as last sync
        mock_notion_client.pages.retrieve.return_value = {
            "last_edited_time": "2025-01-01T12:00:00.000Z",
        }

        changes = await notion_poller.check_for_changes()

        # Should detect no changes (same time as last sync)
        assert len(changes) == 0
        assert mock_notion_client.pages.retrieve.call_count == 2  # Called for both pairs

    @pytest.mark.asyncio
    async def test_check_for_changes_with_changes(
        self, notion_poller, mock_notion_client
    ):
        """Test detecting changes in Notion."""
        # Mock Notion API to return newer timestamp
        mock_notion_client.pages.retrieve.return_value = {
            "last_edited_time": "2025-01-02T12:00:00.000Z",  # Newer than last sync
        }

        changes = await notion_poller.check_for_changes()

        # Should detect changes for both pages
        assert len(changes) == 2
        assert all(isinstance(c, RemoteChange) for c in changes)

        # Check first change
        change = changes[0]
        assert change.pair.id == "pair1"
        assert change.last_edited_time > notion_poller.sync_pairs[0].state.last_sync

    @pytest.mark.asyncio
    async def test_check_for_changes_updates_last_checked(
        self, notion_poller, mock_notion_client
    ):
        """Test that check_for_changes updates last_checked."""
        mock_notion_client.pages.retrieve.return_value = {
            "last_edited_time": "2025-01-02T12:00:00.000Z",
        }

        await notion_poller.check_for_changes()

        # Should have recorded check times
        assert "page-id-1" in notion_poller.last_checked
        assert "page-id-2" in notion_poller.last_checked

    @pytest.mark.asyncio
    async def test_check_for_changes_no_duplicate_detection(
        self, notion_poller, mock_notion_client
    ):
        """Test that changes aren't detected twice."""
        mock_notion_client.pages.retrieve.return_value = {
            "last_edited_time": "2025-01-02T12:00:00.000Z",
        }

        # First check - should find changes
        changes1 = await notion_poller.check_for_changes()
        assert len(changes1) == 2

        # Second check with same time - should find nothing
        changes2 = await notion_poller.check_for_changes()
        assert len(changes2) == 0

    @pytest.mark.asyncio
    async def test_check_for_changes_handles_missing_time(
        self, notion_poller, mock_notion_client
    ):
        """Test handling when last_edited_time is missing."""
        mock_notion_client.pages.retrieve.return_value = {}

        changes = await notion_poller.check_for_changes()

        # Should handle gracefully and return no changes
        assert len(changes) == 0

    @pytest.mark.asyncio
    async def test_check_for_changes_handles_api_error(
        self, notion_poller, mock_notion_client
    ):
        """Test handling Notion API errors."""
        mock_notion_client.pages.retrieve.side_effect = Exception("API Error")

        changes = await notion_poller.check_for_changes()

        # Should handle error and continue checking other pages
        assert len(changes) == 0

    @pytest.mark.asyncio
    async def test_start_and_stop(self, notion_poller):
        """Test starting and stopping poller."""
        mock_callback = AsyncMock()

        # Start poller
        notion_poller.start(mock_callback)
        assert notion_poller.is_running is True
        assert notion_poller.poll_task is not None

        # Wait a bit for poll loop to run
        await asyncio.sleep(0.2)

        # Stop poller
        await notion_poller.stop()
        assert notion_poller.is_running is False

    @pytest.mark.asyncio
    async def test_poll_loop_calls_callback(self, notion_poller, mock_notion_client):
        """Test that poll loop calls callback for changes."""
        mock_callback = AsyncMock()

        # Mock API to return changes
        mock_notion_client.pages.retrieve.return_value = {
            "last_edited_time": "2025-01-02T12:00:00.000Z",
        }

        # Start polling
        notion_poller.start(mock_callback)

        # Wait for at least one poll
        await asyncio.sleep(0.2)

        # Stop polling
        await notion_poller.stop()

        # Callback should have been called
        assert mock_callback.call_count >= 2  # Once for each changed pair

    @pytest.mark.asyncio
    async def test_poll_loop_handles_callback_error(
        self, notion_poller, mock_notion_client
    ):
        """Test that poll loop handles callback errors."""
        mock_callback = AsyncMock(side_effect=Exception("Callback error"))

        # Mock API to return changes
        mock_notion_client.pages.retrieve.return_value = {
            "last_edited_time": "2025-01-02T12:00:00.000Z",
        }

        # Start polling
        notion_poller.start(mock_callback)

        # Wait for poll
        await asyncio.sleep(0.2)

        # Stop - should not crash despite callback errors
        await notion_poller.stop()

    @pytest.mark.asyncio
    async def test_context_manager(self, notion_poller):
        """Test NotionPoller as async context manager."""
        async with notion_poller as poller:
            assert poller == notion_poller

        # Should be stopped after context
        assert notion_poller.is_running is False

    @pytest.mark.asyncio
    async def test_double_start_warning(self, notion_poller):
        """Test that double start is handled gracefully."""
        mock_callback = AsyncMock()

        notion_poller.start(mock_callback)
        notion_poller.start(mock_callback)  # Should log warning

        assert notion_poller.is_running is True

        await notion_poller.stop()

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, notion_poller):
        """Test that stop when not running is handled gracefully."""
        await notion_poller.stop()  # Should log warning but not crash


class TestRemoteChange:
    """Tests for RemoteChange."""

    def test_remote_change_creation(self, sample_sync_pairs):
        """Test RemoteChange creation."""
        pair = sample_sync_pairs[0]
        timestamp = datetime.now(timezone.utc)

        change = RemoteChange(
            pair=pair,
            last_edited_time=timestamp,
        )

        assert change.pair == pair
        assert change.last_edited_time == timestamp

    def test_remote_change_repr(self, sample_sync_pairs):
        """Test RemoteChange string representation."""
        pair = sample_sync_pairs[0]
        timestamp = datetime.now(timezone.utc)

        change = RemoteChange(
            pair=pair,
            last_edited_time=timestamp,
        )

        repr_str = repr(change)
        assert "RemoteChange" in repr_str
        assert "doc1.md" in repr_str
