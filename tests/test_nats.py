"""Unit tests for roxabi_vault.nats.NatsSubscriber."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from roxabi_vault.async_db import AsyncMemoryDB
from roxabi_vault.nats import NatsSubscriber


# ---------------------------------------------------------------------------
# Test subject configuration (via instance attributes)
# ---------------------------------------------------------------------------


def test_default_subject_no_env(monkeypatch) -> None:
    """Uses 'lyra.vault.write' when NATS_SUBJECT env var not set."""
    # Arrange
    monkeypatch.delenv("NATS_SUBJECT", raising=False)
    mock_db = MagicMock(spec=AsyncMemoryDB)

    # Act
    subscriber = NatsSubscriber(db=mock_db)

    # Assert
    assert subscriber.subject == "lyra.vault.write"
    assert subscriber.queue_group == "roxabi-vault"
    assert subscriber.envelope_name == "VaultWrite"
    assert subscriber.schema_version == 1


def test_custom_subject_from_env(monkeypatch) -> None:
    """Uses NATS_SUBJECT env var when set."""
    # Arrange
    monkeypatch.setenv("NATS_SUBJECT", "custom.vault.events")
    mock_db = MagicMock(spec=AsyncMemoryDB)

    # Act
    subscriber = NatsSubscriber(db=mock_db)

    # Assert
    assert subscriber.subject == "custom.vault.events"


def test_custom_subject_from_constructor(monkeypatch) -> None:
    """Constructor subject param overrides NATS_SUBJECT env var."""
    # Arrange
    monkeypatch.setenv("NATS_SUBJECT", "env.vault.topic")
    mock_db = MagicMock(spec=AsyncMemoryDB)

    # Act
    subscriber = NatsSubscriber(db=mock_db, subject="ctor.vault.topic")

    # Assert
    assert subscriber.subject == "ctor.vault.topic"


# ---------------------------------------------------------------------------
# Test run() method
# ---------------------------------------------------------------------------


async def test_run_raises_when_nats_url_missing(monkeypatch) -> None:
    """run() raises ValueError when NATS_URL env var not set."""
    # Arrange
    monkeypatch.delenv("NATS_URL", raising=False)
    mock_db = MagicMock(spec=AsyncMemoryDB)
    subscriber = NatsSubscriber(db=mock_db)

    # Act & Assert
    with pytest.raises(ValueError, match="NATS_URL"):
        await subscriber.run()


async def test_run_uses_nats_url_env(monkeypatch) -> None:
    """run() passes NATS_URL env var to base class run()."""
    # Arrange
    monkeypatch.setenv("NATS_URL", "nats://localhost:4222")
    mock_db = MagicMock(spec=AsyncMemoryDB)
    subscriber = NatsSubscriber(db=mock_db)

    # Act
    with patch.object(
        NatsSubscriber.__bases__[0], "run", new_callable=AsyncMock
    ) as mock_run:
        await subscriber.run()

    # Assert
    mock_run.assert_called_once_with("nats://localhost:4222")


async def test_run_uses_explicit_url_param(monkeypatch) -> None:
    """run() with explicit nats_url param overrides NATS_URL env var."""
    # Arrange
    monkeypatch.setenv("NATS_URL", "nats://env:4222")
    mock_db = MagicMock(spec=AsyncMemoryDB)
    subscriber = NatsSubscriber(db=mock_db)

    # Act
    with patch.object(
        NatsSubscriber.__bases__[0], "run", new_callable=AsyncMock
    ) as mock_run:
        await subscriber.run(nats_url="nats://explicit:4222")

    # Assert
    mock_run.assert_called_once_with("nats://explicit:4222")


# ---------------------------------------------------------------------------
# Test handle() method
# ---------------------------------------------------------------------------


async def test_handle_calls_save_entry() -> None:
    """handle() calls db.save_entry with correct field mapping."""
    # Arrange
    mock_db = MagicMock(spec=AsyncMemoryDB)
    mock_db.save_entry = AsyncMock(return_value=1)
    subscriber = NatsSubscriber(db=mock_db)
    payload = {
        "content": "test content",
        "name": "Test Title",
        "category": "ideas",
        "metadata": {"key": "value"},
    }

    # Act
    await subscriber.handle(None, payload)

    # Assert
    mock_db.save_entry.assert_called_once_with(
        content="test content",
        title="Test Title",
        category="ideas",
        metadata={"key": "value"},
        type="note",
        namespace="vault",
    )


async def test_handle_uses_defaults_for_missing_fields() -> None:
    """handle() uses defaults when optional fields are missing."""
    # Arrange
    mock_db = MagicMock(spec=AsyncMemoryDB)
    mock_db.save_entry = AsyncMock(return_value=1)
    subscriber = NatsSubscriber(db=mock_db)
    payload = {"content": "minimal content"}

    # Act
    await subscriber.handle(None, payload)

    # Assert
    mock_db.save_entry.assert_called_once_with(
        content="minimal content",
        title="",
        category="general",
        metadata=None,
        type="note",
        namespace="vault",
    )
