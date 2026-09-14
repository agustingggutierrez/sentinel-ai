import pytest
from qdrant_client import models

from app.config.settings import Settings
from app.models.retrieval import RetrievalResult
from app.rag.embeddings import SparseEmbeddingVector
from app.rag.qdrant import COLBERT_VECTOR_NAME
from app.rag.retrieval import RetrievalService


class FakeQueryResponse:
    def __init__(
        self,
        points: list[models.ScoredPoint],
    ) -> None:
        self.points = points


class FakeQdrantClient:
    def __init__(
        self,
        points: list[models.ScoredPoint],
    ) -> None:
        self.points = points
        self.calls: list[dict[str, object]] = []

    async def query_points(
        self,
        **kwargs: object,
    ) -> FakeQueryResponse:
        self.calls.append(kwargs)

        return FakeQueryResponse(
            self.points
        )


class FakeEmbeddingService:
    def __init__(self) -> None:
        self.colbert_calls = 0

    async def aembed_dense(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return [
            [0.1] * 384
            for _ in texts
        ]

    async def aembed_sparse(
        self,
        texts: list[str],
    ) -> list[SparseEmbeddingVector]:
        return [
            SparseEmbeddingVector(
                indices=[1, 2, 3],
                values=[1.0, 0.8, 0.5],
            )
            for _ in texts
        ]

    async def aembed_late_interaction(
        self,
        texts: list[str],
    ) -> list[list[list[float]]]:
        self.colbert_calls += 1

        return [
            [
                [0.1] * 96,
                [0.2] * 96,
            ]
            for _ in texts
        ]


def make_point(
    *,
    score: float = 0.9,
) -> models.ScoredPoint:
    return models.ScoredPoint(
        id=1,
        version=1,
        score=score,
        payload={
            "chunk_id": "restricted-areas::001::test",
            "document_id": "restricted-areas",
            "title": "Restricted Areas",
            "category": "restricted_areas",
            "version": "1.0",
            "priority": "critical",
            "document_type": "procedure",
            "section": "Test section",
            "chunk_index": 1,
            "content": "Contenido relevante de prueba.",
            "source_path": "data/documents/test.md",
        },
    )


@pytest.mark.asyncio
async def test_rrf_retrieval_returns_internal_contract() -> None:
    client = FakeQdrantClient(
        [make_point()]
    )

    embeddings = FakeEmbeddingService()

    settings = Settings(
        _env_file=None,
        retrieval_strategy="rrf",
    )

    service = RetrievalService(
        client=client,
        embedding_service=embeddings,
        settings=settings,
    )

    result = await service.retrieve(
        "  acceso a area restringida  "
    )

    assert isinstance(result, RetrievalResult)
    assert result.query == "acceso a area restringida"
    assert result.total_found == 1
    assert len(result.chunks) == 1

    chunk = result.chunks[0]

    assert chunk.document_id == "restricted-areas"
    assert chunk.score == pytest.approx(0.9)
    assert chunk.metadata["category"] == "restricted_areas"
    assert chunk.metadata["priority"] == "critical"


@pytest.mark.asyncio
async def test_rrf_does_not_compute_colbert() -> None:
    client = FakeQdrantClient(
        [make_point()]
    )

    embeddings = FakeEmbeddingService()

    settings = Settings(
        _env_file=None,
        retrieval_strategy="rrf",
    )

    service = RetrievalService(
        client=client,
        embedding_service=embeddings,
        settings=settings,
    )

    await service.retrieve(
        "consulta valida"
    )

    assert embeddings.colbert_calls == 0
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_colbert_strategy_uses_late_interaction() -> None:
    client = FakeQdrantClient(
        [make_point()]
    )

    embeddings = FakeEmbeddingService()

    settings = Settings(
        _env_file=None,
        retrieval_strategy="colbert",
    )

    service = RetrievalService(
        client=client,
        embedding_service=embeddings,
        settings=settings,
    )

    await service.retrieve(
        "consulta valida"
    )

    assert embeddings.colbert_calls == 1
    assert len(client.calls) == 1
    assert (
        client.calls[0]["using"]
        == COLBERT_VECTOR_NAME
    )


def test_metadata_filter_contains_requested_constraints() -> None:
    query_filter = RetrievalService._build_metadata_filter(
        category="restricted_areas",
        priority="critical",
        document_type=None,
        document_id=None,
    )

    assert query_filter is not None
    assert query_filter.must is not None
    assert len(query_filter.must) == 2

    conditions = {
        condition.key: condition.match.value
        for condition in query_filter.must
    }

    assert conditions == {
        "category": "restricted_areas",
        "priority": "critical",
    }


def test_missing_required_payload_is_rejected() -> None:
    point = models.ScoredPoint(
        id=1,
        version=1,
        score=0.5,
        payload={
            "chunk_id": "test::001",
            "document_id": "test",
            "title": "Test",
        },
    )

    with pytest.raises(
        RuntimeError,
        match="missing required payload fields",
    ):
        RetrievalService._point_to_chunk(
            point
        )


@pytest.mark.asyncio
async def test_blank_query_is_rejected() -> None:
    client = FakeQdrantClient(
        []
    )

    embeddings = FakeEmbeddingService()

    settings = Settings(
        _env_file=None,
    )

    service = RetrievalService(
        client=client,
        embedding_service=embeddings,
        settings=settings,
    )

    with pytest.raises(
        ValueError,
        match="at least 3 characters",
    ):
        await service.retrieve("   ")

    assert client.calls == []