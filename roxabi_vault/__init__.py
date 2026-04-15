"""roxabi-vault — persistent memory for Lyra agents and vault skills."""

from .async_db import AsyncMemoryDB
from .db import MemoryDB, MemoryEntry
from .fts import search_fts, search_fts_async
from .namespace import NamespacedReader, NamespacedWriter
from .schema import migrate

__all__ = [
    # S1
    "MemoryDB",
    "MemoryEntry",
    "migrate",
    # S2
    "AsyncMemoryDB",
    "search_fts",
    "search_fts_async",
    "NamespacedReader",
    "NamespacedWriter",
    # S3 — embeddings (optional)
    "Embedder",
    "hybrid_search",
    # S4 — NATS subscriber (optional)
    "NatsSubscriber",
]


def __getattr__(name: str):
    """Lazy import for optional embeddings and NATS symbols."""
    if name == "Embedder":
        from .embeddings import Embedder

        return Embedder
    if name == "hybrid_search":
        from .search import hybrid_search

        return hybrid_search
    if name == "NatsSubscriber":
        from .nats import NatsSubscriber

        return NatsSubscriber
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
