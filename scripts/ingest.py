import asyncio

from app.config.settings import PROJECT_ROOT, get_settings
from app.rag.chunking import build_document_chunks
from app.rag.embeddings import EmbeddingService
from app.rag.ingestion import ingest_chunks
from app.rag.parser import parse_markdown_document
from app.rag.qdrant import create_qdrant_client

DOCUMENTS_PATH = PROJECT_ROOT / "data" / "documents"


async def main() -> None:
    """Parse, chunk, embed and ingest all SentinelAI knowledge documents."""

    settings = get_settings()

    document_paths = sorted(
        DOCUMENTS_PATH.glob("*.md")
    )

    if not document_paths:
        raise RuntimeError(
            f"No Markdown documents found in {DOCUMENTS_PATH}"
        )

    chunks = []

    for document_path in document_paths:
        document = parse_markdown_document(
            document_path
        )

        chunks.extend(
            build_document_chunks(
                document
            )
        )

    client = create_qdrant_client(
        settings
    )

    embedding_service = EmbeddingService(
        settings
    )

    try:
        total_ingested = await ingest_chunks(
            chunks=chunks,
            client=client,
            embedding_service=embedding_service,
            settings=settings,
        )
    finally:
        await client.close()

    print(
        f"Ingested {total_ingested} chunks "
        f"from {len(document_paths)} documents."
    )


if __name__ == "__main__":
    asyncio.run(
        main()
    )