"""NATS subscriber for vault write events."""

import os

from roxabi_nats import NatsAdapterBase

from .async_db import AsyncMemoryDB


class NatsSubscriber(NatsAdapterBase):
    """Subscribe to vault write events from Lyra NATS bus."""

    def __init__(self, db: AsyncMemoryDB, subject: str | None = None) -> None:
        self._db = db
        subject = subject or os.environ.get("NATS_SUBJECT", "lyra.vault.write")
        super().__init__(
            subject=subject,
            queue_group="roxabi-vault",
            envelope_name="VaultWrite",
            schema_version=1,
        )

    async def handle(self, msg, payload: dict) -> None:
        """Process vault write message, store in DB."""
        await self._db.save_entry(
            content=payload["content"],
            title=payload.get("name", ""),
            category=payload.get("category", "general"),
            metadata=payload.get("metadata"),
            type="note",
            namespace="vault",
        )

    async def run(self, nats_url: str | None = None) -> None:
        """Connect to NATS and start subscription loop."""
        url = nats_url or os.environ.get("NATS_URL")
        if not url:
            raise ValueError("NATS_URL env var required")
        await super().run(url)
