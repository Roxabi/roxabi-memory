"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def embedder():
    """Session-scoped Embedder — loads the ONNX model once for all tests."""
    from roxabi_vault.embeddings import Embedder

    return Embedder()
