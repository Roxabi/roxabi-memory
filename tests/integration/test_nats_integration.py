"""Integration test for NatsSubscriber against real NATS server.

Requires Docker to run the NATS container. Tests are skipped if Docker
is not available or NATS server cannot be started.
"""

from __future__ import annotations

import asyncio
import subprocess
import time
from pathlib import Path

import pytest

from roxabi_vault import AsyncMemoryDB, NatsSubscriber


# ---------------------------------------------------------------------------
# Docker/NATS fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def nats_server():
    """Start NATS container via docker-compose, yield URL, then cleanup."""
    compose_file = Path(__file__).parent.parent / "fixtures" / "docker-compose.nats.yml"

    # Check if docker is available
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker not available")

    # Check if compose file exists
    if not compose_file.exists():
        pytest.skip(f"docker-compose.nats.yml not found at {compose_file}")

    # Start NATS
    try:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d"],
            capture_output=True,
            check=True,
            timeout=60,
        )
    except subprocess.CalledProcessError as e:
        pytest.skip(f"Failed to start NATS container: {e.stderr.decode()}")

    # Wait for NATS to be ready
    nats_url = "nats://localhost:4222"
    max_retries = 10
    for i in range(max_retries):
        try:
            result = subprocess.run(
                ["docker", "exec", "roxabi-vault-nats-1", "wget", "-q", "--spider", "http://localhost:8222/healthz"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                break
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
        time.sleep(0.5)
    else:
        # Cleanup on failure
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "down", "-v"],
            capture_output=True,
        )
        pytest.skip("NATS server did not become healthy")

    yield nats_url

    # Cleanup
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "down", "-v"],
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscriber_connects_to_nats(nats_server):
    """Test that NatsSubscriber can connect to a real NATS server."""
    db_path = ":memory:"

    async with AsyncMemoryDB(db_path) as db:
        subscriber = NatsSubscriber(db)

        # Run in background, stop after 2 seconds
        task = asyncio.create_task(subscriber.run(nats_url=nats_server))

        # Wait briefly then cancel
        await asyncio.sleep(0.5)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # If we got here without connection errors, the test passes
        # Connection success is the primary goal of this test


@pytest.mark.asyncio
async def test_subscriber_receives_and_stores_message(nats_server):
    """Test full flow: connect, receive message, store in DB."""
    db_path = ":memory:"
    nats_url = nats_server

    async with AsyncMemoryDB(db_path) as db:
        subscriber = NatsSubscriber(db)

        # Start subscriber in background
        task = asyncio.create_task(subscriber.run(nats_url=nats_url))

        # Give subscriber time to connect
        await asyncio.sleep(0.5)

        # Publish a test message using nats CLI
        # Note: This requires nats CLI to be installed, skip if not
        try:
            publish_result = subprocess.run(
                [
                    "nats", "-s", nats_url, "pub",
                    "lyra.vault.write",
                    '{"content": "integration test note", "name": "Test", "category": "test"}',
                ],
                capture_output=True,
                timeout=10,
            )
            if publish_result.returncode != 0:
                pytest.skip("nats CLI not available or publish failed")
        except FileNotFoundError:
            pytest.skip("nats CLI not installed")

        # Wait for message processing
        await asyncio.sleep(0.5)

        # Cancel subscriber
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify entry was stored
        async with db._db.execute(
            "SELECT title, content, category FROM entries"
        ) as cur:
            rows = await cur.fetchall()

        # Should have at least one entry
        assert len(rows) >= 1
        # Find the test entry
        test_entries = [r for r in rows if r[1] == "integration test note"]
        assert len(test_entries) == 1
        assert test_entries[0][0] == "Test"
        assert test_entries[0][2] == "test"
