from qdrant_client import AsyncQdrantClient, models

from app.config.settings import Settings, get_settings


DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"
COLBERT_VECTOR_NAME = "colbert"

DENSE_VECTOR_SIZE = 384
COLBERT_VECTOR_SIZE = 96


def create_qdrant_client(
    settings: Settings | None = None,
) -> AsyncQdrantClient:
    """Create an async Qdrant client for local or server mode."""

    resolved_settings = settings or get_settings()

    if resolved_settings.qdrant_mode == "local":
        storage_path = resolved_settings.qdrant_storage_path
        storage_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        return AsyncQdrantClient(
            path=str(storage_path),
        )

    return AsyncQdrantClient(
        url=resolved_settings.qdrant_url,
        api_key=resolved_settings.qdrant_api_key or None,
    )


def build_dense_vectors_config() -> dict[str, models.VectorParams]:
    """Return the named dense and late-interaction vector schema."""

    return {
        DENSE_VECTOR_NAME: models.VectorParams(
            size=DENSE_VECTOR_SIZE,
            distance=models.Distance.COSINE,
        ),
        COLBERT_VECTOR_NAME: models.VectorParams(
            size=COLBERT_VECTOR_SIZE,
            distance=models.Distance.COSINE,
            multivector_config=models.MultiVectorConfig(
                comparator=models.MultiVectorComparator.MAX_SIM,
            ),
            hnsw_config=models.HnswConfigDiff(
                m=0,
            ),
        ),
    }


def build_sparse_vectors_config() -> dict[str, models.SparseVectorParams]:
    """Return the named sparse BM25 vector schema."""

    return {
        SPARSE_VECTOR_NAME: models.SparseVectorParams(
            modifier=models.Modifier.IDF,
        ),
    }


async def ensure_qdrant_collection(
    client: AsyncQdrantClient,
    settings: Settings | None = None,
) -> bool:
    """Create the SentinelAI collection if it does not already exist."""

    resolved_settings = settings or get_settings()
    collection_name = resolved_settings.qdrant_collection_name

    if await client.collection_exists(collection_name):
        return False

    await client.create_collection(
        collection_name=collection_name,
        vectors_config=build_dense_vectors_config(),
        sparse_vectors_config=build_sparse_vectors_config(),
    )

    return True