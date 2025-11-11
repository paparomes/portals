"""Core sync engine for bidirectional synchronization."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from portals.core.conflict_detector import ConflictDetector
from portals.core.exceptions import ConflictError, SyncError
from portals.core.models import Document, SyncPair, SyncPairState, SyncResult, SyncStatus

if TYPE_CHECKING:
    from portals.adapters.base import DocumentAdapter

logger = logging.getLogger(__name__)


class SyncEngine:
    """Core sync engine implementing 3-way merge algorithm.

    Handles bidirectional synchronization between local and remote documents
    using conflict detection and automatic push/pull operations.
    """

    def __init__(
        self,
        local_adapter: DocumentAdapter,
        remote_adapter: DocumentAdapter,
    ) -> None:
        """Initialize sync engine.

        Args:
            local_adapter: Adapter for local file operations
            remote_adapter: Adapter for remote platform operations
        """
        self.local_adapter = local_adapter
        self.remote_adapter = remote_adapter
        self.conflict_detector = ConflictDetector()

    async def sync_pair(
        self,
        pair: SyncPair,
        force_direction: str | None = None,
    ) -> SyncResult:
        """Sync a single document pair.

        Args:
            pair: Sync pair with local/remote URIs and state
            force_direction: Optional force direction ("push" or "pull"), ignores conflicts

        Returns:
            SyncResult with operation outcome

        Raises:
            SyncError: If sync operation fails
            ConflictError: If conflict detected and not forced
        """
        try:
            logger.info(f"Syncing pair: {pair.local_path} <-> {pair.remote_uri}")

            # Read current state from both sides
            local_doc = await self.local_adapter.read(f"file://{pair.local_path}")
            remote_doc = await self.remote_adapter.read(pair.remote_uri)

            local_current_hash = local_doc.content_hash or ""
            remote_current_hash = remote_doc.content_hash or ""

            # Get last synced hash
            if not pair.state:
                # First sync - treat as identical base
                last_synced_hash = ""
            else:
                last_synced_hash = pair.state.last_synced_hash

            # Handle forced direction
            if force_direction:
                return await self._sync_forced(
                    pair,
                    local_doc,
                    remote_doc,
                    force_direction,
                    local_current_hash,
                    remote_current_hash,
                )

            # Detect conflicts
            decision = self.conflict_detector.detect(
                local_hash=local_current_hash,
                remote_hash=remote_current_hash,
                base_hash=last_synced_hash,
            )

            logger.info(f"Sync decision: {decision.status.value} - {decision.reason}")

            # Handle based on decision
            if decision.status == SyncStatus.NO_CHANGES:
                return SyncResult(
                    status=SyncStatus.NO_CHANGES,
                    message="No changes detected",
                    local_path=pair.local_path,
                    remote_uri=pair.remote_uri,
                )

            elif decision.status == SyncStatus.CONFLICT:
                raise ConflictError(
                    f"Conflict detected for {pair.local_path}: {decision.reason}",
                    local_hash=local_current_hash,
                    remote_hash=remote_current_hash,
                )

            # Perform sync based on decision
            if decision.should_push:
                await self.remote_adapter.write(pair.remote_uri, local_doc)
                new_hash = local_current_hash
                message = "Pushed local changes to remote"

            elif decision.should_pull:
                await self.local_adapter.write(f"file://{pair.local_path}", remote_doc)
                new_hash = remote_current_hash
                message = "Pulled remote changes to local"

            else:
                # Identical changes - just update base hash
                new_hash = local_current_hash
                message = "Synchronized identical changes"

            # Update pair state
            pair.state = SyncPairState(
                local_hash=new_hash,
                remote_hash=new_hash,
                last_synced_hash=new_hash,
                last_sync=datetime.now(),
                has_conflict=False,
            )

            return SyncResult(
                status=SyncStatus.SUCCESS,
                message=message,
                local_path=pair.local_path,
                remote_uri=pair.remote_uri,
            )

        except ConflictError:
            # Mark conflict in state
            if pair.state:
                pair.state.has_conflict = True
            raise

        except Exception as e:
            logger.error(f"Sync failed for {pair.local_path}: {e}")
            if pair.state:
                pair.state.last_error = str(e)
            raise SyncError(f"Failed to sync {pair.local_path}: {e}") from e

    async def _sync_forced(
        self,
        pair: SyncPair,
        local_doc: Document,
        remote_doc: Document,
        direction: str,
        local_hash: str,
        remote_hash: str,
    ) -> SyncResult:
        """Perform forced sync in specified direction.

        Args:
            pair: Sync pair
            local_doc: Local document
            remote_doc: Remote document
            direction: "push" or "pull"
            local_hash: Current local hash
            remote_hash: Current remote hash

        Returns:
            SyncResult

        Raises:
            SyncError: If invalid direction or sync fails
        """
        if direction == "push":
            await self.remote_adapter.write(pair.remote_uri, local_doc)
            new_hash = local_hash
            message = "Force pushed local changes to remote"

        elif direction == "pull":
            await self.local_adapter.write(f"file://{pair.local_path}", remote_doc)
            new_hash = remote_hash
            message = "Force pulled remote changes to local"

        else:
            raise SyncError(f"Invalid force direction: {direction}")

        # Update pair state
        pair.state = SyncPairState(
            local_hash=new_hash,
            remote_hash=new_hash,
            last_synced_hash=new_hash,
            last_sync=datetime.now(),
            has_conflict=False,
        )

        logger.info(f"Forced sync {direction}: {pair.local_path}")

        return SyncResult(
            status=SyncStatus.SUCCESS,
            message=message,
            local_path=pair.local_path,
            remote_uri=pair.remote_uri,
        )

    async def push(self, pair: SyncPair) -> SyncResult:
        """Force push local changes to remote (ignore conflicts).

        Args:
            pair: Sync pair

        Returns:
            SyncResult
        """
        return await self.sync_pair(pair, force_direction="push")

    async def pull(self, pair: SyncPair) -> SyncResult:
        """Force pull remote changes to local (ignore conflicts).

        Args:
            pair: Sync pair

        Returns:
            SyncResult
        """
        return await self.sync_pair(pair, force_direction="pull")
