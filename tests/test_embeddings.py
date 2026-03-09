"""Tests for roxabi_memory.embeddings — Embedder (S3 Slice 1)."""

from __future__ import annotations

import struct

import pytest


# ---------------------------------------------------------------------------
# T1: embed() returns 384-dim float32 bytes
# ---------------------------------------------------------------------------


def test_embed_returns_float32_blob(embedder):
    result = embedder.embed("hello world")
    assert isinstance(result, bytes)
    assert len(result) == 384 * 4  # float32 × 384


def test_embed_values_are_finite_floats(embedder):
    blob = embedder.embed("test sentence")
    floats = struct.unpack(f"{384}f", blob)
    assert all(isinstance(v, float) for v in floats)
    assert all(abs(v) < 100 for v in floats)  # sane magnitude


def test_model_loaded_once(embedder):
    embedder.embed("first")
    model_id = id(embedder._model)
    embedder.embed("second")
    assert id(embedder._model) == model_id


# ---------------------------------------------------------------------------
# T2: embed_async() uses run_in_executor
# ---------------------------------------------------------------------------


async def test_embed_async_returns_same_as_sync(embedder):
    sync_result = embedder.embed("test text")
    async_result = await embedder.embed_async("test text")
    assert sync_result == async_result


async def test_embed_async_returns_bytes(embedder):
    result = await embedder.embed_async("async test")
    assert isinstance(result, bytes)
    assert len(result) == 384 * 4


# ---------------------------------------------------------------------------
# T15: ImportError when fastembed not installed
# ---------------------------------------------------------------------------


def test_import_error_when_fastembed_missing(monkeypatch):
    """Importing Embedder when fastembed is unavailable raises ImportError."""
    import importlib
    import sys

    # Remove cached module
    mods_to_remove = [
        k for k in sys.modules if k.startswith("roxabi_memory.embeddings")
    ]
    for m in mods_to_remove:
        del sys.modules[m]

    # Block fastembed import
    original_import = (
        __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
    )

    def mock_import(name, *args, **kwargs):
        if name == "fastembed" or name.startswith("fastembed."):
            raise ImportError("mocked: no fastembed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import)

    with pytest.raises(ImportError, match="fastembed"):
        importlib.import_module("roxabi_memory.embeddings")

    # Cleanup: restore module cache
    mods_to_remove = [
        k for k in sys.modules if k.startswith("roxabi_memory.embeddings")
    ]
    for m in mods_to_remove:
        del sys.modules[m]
