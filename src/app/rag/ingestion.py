from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import AsyncQdrantClient, models

from app.config.settings import Settings, get_settings
from app.models.chunk import DocumentChunk
from app.rag.embeddings import EmbeddingService
from app.rag.qdrant import (
    COLBERT_VECTOR_NAME,
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    ensure_qdrant_collection,
)


def build_point_id(chunk_id: str) -> str:
    """Create a stable UUID from a deterministic SentinelAI chunk ID."""

    if not chunk_id.strip():
        raise ValueError("chunk_id cannot be blank")

    return str(
        uuid5(
            NAMESPACE_URL,
            f"sentinel-ai:{chunk_id}",
        )
    )


def build_chunk_payload(
    chunk: DocumentChunk,
) -> dict[str, str | int]:
    """Build the Qdrant payload associated with a document chunk."""

    return {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "title": chunk.title,
        "category": chunk.category,
        "version": chunk.version,
        "priority": chunk.priority,
        "document_type": chunk.document_type,
        "section": chunk.section,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        "source_path": chunk.source_path,
    }


async def build_qdrant_point(
    chunk: DocumentChunk,
    embedding_service: EmbeddingService,
) -> models.PointStruct:
    """Embed one chunk and convert it into a Qdrant point."""

    points = await build_qdrant_points(
        chunks=[chunk],
        embedding_service=embedding_service,
    )

    return points[0]


async def build_qdrant_points(
    chunks: Sequence[DocumentChunk],
    embedding_service: EmbeddingService,
) -> list[models.PointStruct]:
    """Embed a batch of chunks and convert them into Qdrant points."""

    if not chunks:
        raise ValueError(
            "At least one DocumentChunk is required."
        )

    texts = [
        chunk.content
        for chunk in chunks
    ]

    dense_embeddings = await embedding_service.aembed_dense(
        texts
    )

    sparse_embeddings = await embedding_service.aembed_sparse(
        texts
    )

    colbert_embeddings = await embedding_service.aembed_late_interaction(
        texts
    )

    expected_count = len(chunks)

    if not (
        len(dense_embeddings)
        == len(sparse_embeddings)
        == len(colbert_embeddings)
        == expected_count
    ):
        raise RuntimeError(
            "Embedding batch sizes do not match the chunk batch size."
        )

    points: list[models.PointStruct] = []

    for (
        chunk,
        dense,
        sparse,
        colbert,
    ) in zip(
        chunks,
        dense_embeddings,
        sparse_embeddings,
        colbert_embeddings,
        strict=True,
    ):
        points.append(
            models.PointStruct(
                id=build_point_id(chunk.chunk_id),
                vector={
                    DENSE_VECTOR_NAME: dense,
                    SPARSE_VECTOR_NAME: models.SparseVector(
                        indices=sparse.indices,
                        values=sparse.values,
                    ),
                    COLBERT_VECTOR_NAME: colbert,
                },
                payload=build_chunk_payload(chunk),
            )
        )

    return points


async def ingest_chunks(
    *,
    chunks: Sequence[DocumentChunk],
    client: AsyncQdrantClient,
    embedding_service: EmbeddingService,
    settings: Settings | None = None,
) -> int:
    """Embed and upsert document chunks into Qdrant in bounded batches."""

    if not chunks:
        raise ValueError(
            "At least one DocumentChunk is required for ingestion."
        )

    resolved_settings = settings or get_settings()

    await ensure_qdrant_collection(
        client=client,
        settings=resolved_settings,
    )

    total_ingested = 0
    batch_size = resolved_settings.ingestion_batch_size

    for start in range(0, len(chunks), batch_size):
        batch = chunks[
            start : start + batch_size
        ]

        points = await build_qdrant_points(
            chunks=batch,
            embedding_service=embedding_service,
        )

        await client.upsert(
            collection_name=resolved_settings.qdrant_collection_name,
            points=points,
            wait=True,
        )

        total_ingested += len(points)

    return total_ingested