"""Background task to expire pending HITL approvals."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devhub.domain.ports import IHITLApprovalRepository

logger = logging.getLogger(__name__)


class ExpireApprovalsTask:
    """Periodically expires pending approvals that have passed their TTL."""

    def __init__(self, approval_repo: IHITLApprovalRepository, interval_seconds: int = 60) -> None:
        self._approval_repo = approval_repo
        self._interval = interval_seconds
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the background expiration task."""
        if self._running:
            logger.warning("ExpireApprovalsTask already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("ExpireApprovalsTask started")

    async def stop(self) -> None:
        """Stop the background expiration task."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("ExpireApprovalsTask stopped")

    async def _run_loop(self) -> None:
        """Main loop that periodically expires approvals."""
        while self._running:
            try:
                expired_ids = await self._approval_repo.expire_pending()
                if expired_ids:
                    logger.info(f"Expired {len(expired_ids)} pending approvals: {expired_ids}")
            except Exception:
                logger.exception("Error expiring approvals")

            await asyncio.sleep(self._interval)
