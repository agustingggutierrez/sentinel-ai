import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property, lru_cache

from fastembed import (
    LateInteractionTextEmbedding,
    SparseTextEmbedding,
    TextEmbedding,
)
from fastembed.common.model_description import (
    ModelSource,
    PoolingType,
)

from app.config.settings import Settings, get_settings


@dataclass(frozen=True, slots=True)
class SparseEmbeddingVector:
    """Framework-independent sparse embedding representation."""

    indices: list[int]
    values: list[float]


_LEGACY_DENSE_MODEL = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)

_SENTINEL_DENSE_MODEL_ALIAS = (
    "sentinel/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)


def _ensure_dense_model_alias() -> None:
    """Register a warning-free alias matching FastEmbed 0.8.0 behavior."""

    supported_models = {
        model["model"]
        for model in TextEmbedding.list_supported_models()
    }

    if _SENTINEL_DENSE_MODEL_ALIAS in supported_models:
        return

    TextEmbedding.add_custom_model(
        model=_SENTINEL_DENSE_MODEL_ALIAS,
        pooling=PoolingType.MEAN,
        normalization=False,
        sources=ModelSource(
            hf=(
                "qdrant/"
                "paraphrase-multilingual-MiniLM-L12-v2-onnx-Q"
            ),
        ),
        dim=384,
        model_file="model_optimized.onnx",
        description=(
            "SentinelAI compatibility alias preserving "
            "FastEmbed 0.8.0 mean pooling behavior."
        ),
        license="apache-2.0",
        size_in_gb=0.22,
    )


class EmbeddingService:
    """Centralized dense, sparse and late-interaction embedding service."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @cached_property
    def dense_model(self) -> TextEmbedding:
        """Load and cache the configured dense embedding model."""

        model_name = self.settings.dense_embedding_model

        if model_name == _LEGACY_DENSE_MODEL:
            _ensure_dense_model_alias()
            model_name = _SENTINEL_DENSE_MODEL_ALIAS

        return TextEmbedding(
            model_name=model_name,
        )

    @cached_property
    def sparse_model(self) -> SparseTextEmbedding:
        """Load and cache the configured sparse embedding model."""

        return SparseTextEmbedding(
            model_name=self.settings.sparse_embedding_model,
        )

    @cached_property
    def rerank_model(self) -> LateInteractionTextEmbedding:
        """Load and cache the configured late-interaction model."""

        return LateInteractionTextEmbedding(
            model_name=self.settings.rerank_model,
        )

    def embed_dense(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        """Generate dense embeddings for one or more texts."""

        validated_texts = self._validate_texts(texts)

        return [
            embedding.tolist()
            for embedding in self.dense_model.embed(validated_texts)
        ]

    def embed_sparse(
        self,
        texts: Sequence[str],
    ) -> list[SparseEmbeddingVector]:
        """Generate sparse BM25 representations."""

        validated_texts = self._validate_texts(texts)

        return [
            SparseEmbeddingVector(
                indices=embedding.indices.tolist(),
                values=embedding.values.tolist(),
            )
            for embedding in self.sparse_model.embed(validated_texts)
        ]

    def embed_late_interaction(
        self,
        texts: Sequence[str],
    ) -> list[list[list[float]]]:
        """Generate ColBERT-style multi-vector embeddings."""

        validated_texts = self._validate_texts(texts)

        return [
            embedding.tolist()
            for embedding in self.rerank_model.embed(validated_texts)
        ]

    async def aembed_dense(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        """Generate dense embeddings without blocking the event loop."""

        return await asyncio.to_thread(
            self.embed_dense,
            texts,
        )

    async def aembed_sparse(
        self,
        texts: Sequence[str],
    ) -> list[SparseEmbeddingVector]:
        """Generate sparse embeddings without blocking the event loop."""

        return await asyncio.to_thread(
            self.embed_sparse,
            texts,
        )

    async def aembed_late_interaction(
        self,
        texts: Sequence[str],
    ) -> list[list[list[float]]]:
        """Generate late-interaction embeddings asynchronously."""

        return await asyncio.to_thread(
            self.embed_late_interaction,
            texts,
        )

    @staticmethod
    def _validate_texts(
        texts: Sequence[str],
    ) -> list[str]:
        """Reject empty batches and blank text values."""

        validated = [
            text.strip()
            for text in texts
        ]

        if not validated:
            raise ValueError(
                "At least one text is required for embedding."
            )

        if any(not text for text in validated):
            raise ValueError(
                "Embedding texts cannot be blank."
            )

        return validated


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Return the shared embedding service instance."""

    return EmbeddingService(
        settings=get_settings(),
    )