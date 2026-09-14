from pathlib import Path

import pytest
from qdrant_client import models

from app.config.settings import Settings
from app.rag.embeddings import SparseEmbeddingVector
from app.rag.qdrant import (
    COLBERT_VECTOR_NAME,
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    create_qdrant_client,
    ensure_qdrant_collection,
)
from app.rag.retrieval import RetrievalService


class DeterministicEmbeddingService:
    async def aembed_dense(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        vector = [0.0] * 384
        vector[0] = 1.0

        return [
            vector.copy()
            for _ in texts
        ]

    async def aembed_sparse(
        self,
        texts: list[str],
    ) -> list[SparseEmbeddingVector]:
        return [
            SparseEmbeddingVector(
                indices=[1],
                values=[1.0],
            )
            for _ in texts
        ]

    async def aembed_late_interaction(
        self,
        texts: list[str],
    ) -> list[list[list[float]]]:
        vector = [0.0] * 96
        vector[0] = 1.0

        return [
            [vector.copy()]
            for _ in texts
        ]


def build_settings(
    tmp_path: Path,
) -> Settings:
    return Settings(
        _env_file=None,
        qdrant_mode="local",
        qdrant_local_path=tmp_path / "qdrant",
        qdrant_collection_name="sentinel_ai_test",
        retrieval_strategy="rrf",
        dense_prefetch_limit=5,
        sparse_prefetch_limit=5,
        retrieval_candidate_limit=5,
        retrieval_top_k=5,
    )


def build_points() -> list[models.PointStruct]:
    restricted_dense = [0.0] * 384
    restricted_dense[0] = 1.0

    visitor_dense = [0.0] * 384
    visitor_dense[1] = 1.0

    colbert = [0.0] * 96
    colbert[0] = 1.0

    return [
        models.PointStruct(
            id=1,
            vector={
                DENSE_VECTOR_NAME: restricted_dense,
                SPARSE_VECTOR_NAME: models.SparseVector(
                    indices=[1],
                    values=[1.0],
                ),
                COLBERT_VECTOR_NAME: [
                    colbert.copy()
                ],
            },
            payload={
                "chunk_id": "restricted-areas::001::integration",
                "document_id": "restricted-areas",
                "title": "Restricted Areas",
                "category": "restricted_areas",
                "version": "1.0",
                "priority": "critical",
                "document_type": "procedure",
                "section": "Acceso no autorizado",
                "chunk_index": 1,
                "content": (
                    "Una persona sin autorización no puede ingresar "
                    "a un área restringida."
                ),
                "source_path": "data/documents/restricted.md",
            },
        ),
        models.PointStruct(
            id=2,
            vector={
                DENSE_VECTOR_NAME: visitor_dense,
                SPARSE_VECTOR_NAME: models.SparseVector(
                    indices=[2],
                    values=[1.0],
                ),
                COLBERT_VECTOR_NAME: [
                    colbert.copy()
                ],
            },
            payload={
                "chunk_id": "visitor-management::001::integration",
                "document_id": "visitor-management",
                "title": "Visitor Management",
                "category": "visitor_management",
                "version": "1.0",
                "priority": "high",
                "document_type": "procedure",
                "section": "Registro de visitantes",
                "chunk_index": 1,
                "content": (
                    "Todo visitante debe ser identificado antes "
                    "de autorizar su ingreso."
                ),
                "source_path": "data/documents/visitor.md",
            },
        ),
    ]


@pytest.mark.asyncio
async def test_collection_creation_is_idempotent(
    tmp_path: Path,
) -> None:
    settings = build_settings(tmp_path)
    client = create_qdrant_client(settings)

    try:
        first_creation = await ensure_qdrant_collection(
            client,
            settings,
        )

        second_creation = await ensure_qdrant_collection(
            client,
            settings,
        )

        assert first_creation is True
        assert second_creation is False

        assert await client.collection_exists(
            settings.qdrant_collection_name
        )
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_real_qdrant_hybrid_retrieval_and_filter(
    tmp_path: Path,
) -> None:
    settings = build_settings(tmp_path)
    client = create_qdrant_client(settings)

    try:
        await ensure_qdrant_collection(
            client,
            settings,
        )

        await client.upsert(
            collection_name=settings.qdrant_collection_name,
            points=build_points(),
            wait=True,
        )

        collection = await client.get_collection(
            settings.qdrant_collection_name
        )

        assert collection.points_count == 2

        service = RetrievalService(
            client=client,
            embedding_service=DeterministicEmbeddingService(),
            settings=settings,
        )

        result = await service.retrieve(
            "persona sin autorizacion en area restringida"
        )

        assert result.total_found == 2
        assert result.chunks[0].document_id == "restricted-areas"

        filtered_result = await service.retrieve(
            "persona sin autorizacion en area restringida",
            category="visitor_management",
        )

        assert filtered_result.total_found == 1
        assert (
            filtered_result.chunks[0].document_id
            == "visitor-management"
        )
        assert (
            filtered_result.chunks[0].metadata["category"]
            == "visitor_management"
        )
    finally:
        await client.close()