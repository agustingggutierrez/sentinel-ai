import asyncio

from qdrant_client import AsyncQdrantClient, models

from app.config.settings import Settings, get_settings
from app.models.retrieval import RetrievalResult, RetrievedChunk
from app.rag.embeddings import EmbeddingService, get_embedding_service
from app.rag.qdrant import (
    COLBERT_VECTOR_NAME,
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    create_qdrant_client,
)


class RetrievalService:
    """Hybrid retrieval service backed by Qdrant."""

    def __init__(
        self,
        *,
        client: AsyncQdrantClient,
        embedding_service: EmbeddingService,
        settings: Settings,
    ) -> None:
        self.client = client
        self.embedding_service = embedding_service
        self.settings = settings

    async def retrieve(
        self,
        query: str,
        *,
        category: str | None = None,
        priority: str | None = None,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> RetrievalResult:
        """Retrieve relevant chunks using optional metadata filters."""

        normalized_query = query.strip()

        if len(normalized_query) < 3:
            raise ValueError(
                "Retrieval query must contain at least 3 characters."
            )

        query_filter = self._build_metadata_filter(
            category=category,
            priority=priority,
            document_type=document_type,
            document_id=document_id,
        )

        dense_task = self.embedding_service.aembed_dense(
            [normalized_query]
        )

        sparse_task = self.embedding_service.aembed_sparse(
            [normalized_query]
        )

        dense_embeddings, sparse_embeddings = await asyncio.gather(
            dense_task,
            sparse_task,
        )

        dense = dense_embeddings[0]
        sparse_embedding = sparse_embeddings[0]

        sparse = models.SparseVector(
            indices=sparse_embedding.indices,
            values=sparse_embedding.values,
        )

        if self.settings.retrieval_strategy == "colbert":
            points = await self._retrieve_with_colbert(
                query=normalized_query,
                dense=dense,
                sparse=sparse,
                query_filter=query_filter,
            )
        else:
            points = await self._retrieve_with_rrf(
                dense=dense,
                sparse=sparse,
                query_filter=query_filter,
            )

        chunks = [
            self._point_to_chunk(point)
            for point in points
        ]

        return RetrievalResult(
            query=normalized_query,
            chunks=chunks,
            total_found=len(chunks),
        )

    async def _retrieve_with_rrf(
        self,
        *,
        dense: list[float],
        sparse: models.SparseVector,
        query_filter: models.Filter | None,
    ) -> list[models.ScoredPoint]:
        """Run dense + sparse retrieval fused with RRF."""

        result = await self.client.query_points(
            collection_name=self.settings.qdrant_collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense,
                    using=DENSE_VECTOR_NAME,
                    filter=query_filter,
                    limit=self.settings.dense_prefetch_limit,
                ),
                models.Prefetch(
                    query=sparse,
                    using=SPARSE_VECTOR_NAME,
                    filter=query_filter,
                    limit=self.settings.sparse_prefetch_limit,
                ),
            ],
            query=models.FusionQuery(
                fusion=models.Fusion.RRF,
            ),
            limit=self.settings.retrieval_top_k,
            with_payload=True,
            with_vectors=False,
        )

        return result.points

    async def _retrieve_with_colbert(
        self,
        *,
        query: str,
        dense: list[float],
        sparse: models.SparseVector,
        query_filter: models.Filter | None,
    ) -> list[models.ScoredPoint]:
        """Run hybrid RRF retrieval followed by ColBERT reranking."""

        colbert_embeddings = (
            await self.embedding_service.aembed_late_interaction(
                [query]
            )
        )

        colbert = colbert_embeddings[0]

        hybrid_prefetch = models.Prefetch(
            prefetch=[
                models.Prefetch(
                    query=dense,
                    using=DENSE_VECTOR_NAME,
                    filter=query_filter,
                    limit=self.settings.dense_prefetch_limit,
                ),
                models.Prefetch(
                    query=sparse,
                    using=SPARSE_VECTOR_NAME,
                    filter=query_filter,
                    limit=self.settings.sparse_prefetch_limit,
                ),
            ],
            query=models.FusionQuery(
                fusion=models.Fusion.RRF,
            ),
            limit=self.settings.retrieval_candidate_limit,
        )

        result = await self.client.query_points(
            collection_name=self.settings.qdrant_collection_name,
            prefetch=hybrid_prefetch,
            query=colbert,
            using=COLBERT_VECTOR_NAME,
            limit=self.settings.retrieval_top_k,
            with_payload=True,
            with_vectors=False,
        )

        return result.points

    @staticmethod
    def _build_metadata_filter(
        *,
        category: str | None,
        priority: str | None,
        document_type: str | None,
        document_id: str | None,
    ) -> models.Filter | None:
        """Build a Qdrant filter from optional metadata constraints."""

        raw_filters = {
            "category": category,
            "priority": priority,
            "document_type": document_type,
            "document_id": document_id,
        }

        conditions: list[models.FieldCondition] = []

        for field_name, raw_value in raw_filters.items():
            if raw_value is None:
                continue

            normalized_value = raw_value.strip()

            if not normalized_value:
                raise ValueError(
                    f"Metadata filter '{field_name}' cannot be blank."
                )

            conditions.append(
                models.FieldCondition(
                    key=field_name,
                    match=models.MatchValue(
                        value=normalized_value,
                    ),
                )
            )

        if not conditions:
            return None

        return models.Filter(
            must=conditions,
        )

    @staticmethod
    def _point_to_chunk(
        point: models.ScoredPoint,
    ) -> RetrievedChunk:
        """Convert a Qdrant result into the internal retrieval contract."""

        payload = point.payload or {}

        required_fields = (
            "chunk_id",
            "document_id",
            "title",
            "content",
        )

        missing_fields = [
            field
            for field in required_fields
            if not payload.get(field)
        ]

        if missing_fields:
            raise RuntimeError(
                "Retrieved Qdrant point is missing required payload fields: "
                + ", ".join(missing_fields)
            )

        metadata = {
            key: payload[key]
            for key in (
                "category",
                "version",
                "priority",
                "document_type",
                "section",
                "chunk_index",
                "source_path",
            )
            if key in payload
        }

        return RetrievedChunk(
            document_id=str(payload["document_id"]),
            title=str(payload["title"]),
            chunk_id=str(payload["chunk_id"]),
            content=str(payload["content"]),
            score=float(point.score),
            metadata=metadata,
        )


def create_retrieval_service(
    *,
    settings: Settings | None = None,
) -> RetrievalService:
    """Create a retrieval service using application configuration."""

    resolved_settings = settings or get_settings()

    return RetrievalService(
        client=create_qdrant_client(resolved_settings),
        embedding_service=get_embedding_service(),
        settings=resolved_settings,
    )