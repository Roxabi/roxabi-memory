"""Embedding support via fastembed ONNX — optional dependency."""

from __future__ import annotations

import asyncio
import struct

try:
    from fastembed import TextEmbedding
except ImportError as exc:
    raise ImportError(
        "fastembed is required for embeddings: pip install roxabi-memory[embeddings]"
    ) from exc


class Embedder:
    """Wraps fastembed TextEmbedding. Loads ONNX model once at init."""

    MODEL_NAME = "BAAI/bge-small-en-v1.5"
    DIMENSION = 384

    def __init__(self) -> None:
        self._model = TextEmbedding(model_name=self.MODEL_NAME)

    @property
    def dimension(self) -> int:
        return self.DIMENSION

    def embed(self, text: str) -> bytes:
        """Compute embedding and return as float32 BLOB."""
        vectors = list(self._model.embed([text]))
        vec = vectors[0]
        if len(vec) != self.DIMENSION:
            raise ValueError(
                f"Model returned {len(vec)}-dim vector, expected {self.DIMENSION}"
            )
        magnitude = sum(v * v for v in vec) ** 0.5
        if magnitude == 0.0:
            raise ValueError("Model returned zero-magnitude vector")
        return struct.pack(f"{self.DIMENSION}f", *vec)

    async def embed_async(self, text: str) -> bytes:
        """Async wrapper — runs embed() in a thread via run_in_executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.embed, text)
