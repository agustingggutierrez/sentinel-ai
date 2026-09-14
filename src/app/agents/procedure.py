import asyncio
from typing import Protocol

from app.graph.state import SentinelState
from app.models.response import SourceReference
from app.models.retrieval import RetrievalResult, RetrievedChunk


class RetrievalPort(Protocol):
    """Minimal retrieval interface required by the Procedure Agent."""

    async def retrieve(
        self,
        query: str,
        *,
        category: str | None = None,
        priority: str | None = None,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> RetrievalResult:
        """Retrieve relevant procedural evidence."""


class ProcedureAgentService:
    """Retrieve procedural evidence required by the graph."""

    def __init__(
        self,
        retrieval_service: RetrievalPort,
        *,
        retry_evidence_limit: int = 10,
    ) -> None:
        if retry_evidence_limit < 1:
            raise ValueError(
                "retry_evidence_limit must be at least 1."
            )

        self.retrieval_service = retrieval_service
        self.retry_evidence_limit = retry_evidence_limit

    async def run(
        self,
        state: SentinelState,
    ) -> dict[str, object]:
        """Retrieve evidence and update the shared graph state."""

        query = state["query"]

        verification = state.get(
            "verification_result"
        )

        is_retry = (
            verification is not None
            and verification.status == "needs_more_evidence"
        )

        if (
            is_retry
            and verification.missing_information
        ):
            retrieval_queries = self._build_retry_queries(
                query=query,
                missing_information=verification.missing_information,
            )

            results = await asyncio.gather(
                *(
                    self.retrieval_service.retrieve(
                        retrieval_query
                    )
                    for retrieval_query in retrieval_queries
                )
            )

            chunks = self._fuse_results(
                results
            )
        else:
            result = await self.retrieval_service.retrieve(
                query
            )

            chunks = result.chunks

        sources = [
            SourceReference(
                document_id=chunk.document_id,
                title=chunk.title,
                chunk_id=chunk.chunk_id,
                score=chunk.score,
            )
            for chunk in chunks
        ]

        retry_count = state.get(
            "retry_count",
            0,
        )

        if is_retry:
            retry_count += 1

        agents_used = [
            *state.get(
                "agents_used",
                [],
            ),
            "procedure_agent",
        ]

        update: dict[str, object] = {
            "retrieved_documents": chunks,
            "sources": sources,
            "retry_count": retry_count,
            "agents_used": agents_used,
        }

        if is_retry:
            update["verification_result"] = None
            update["incident_analysis"] = None

        return update

    @staticmethod
    def _build_retry_queries(
        *,
        query: str,
        missing_information: list[str],
    ) -> list[str]:
        """Build distinct retrieval queries for a verification retry."""

        queries = [query]

        for item in missing_information:
            normalized = item.strip()

            if (
                normalized
                and normalized not in queries
            ):
                queries.append(
                    normalized
                )

        return queries

    def _fuse_results(
        self,
        results: list[RetrievalResult],
    ) -> list[RetrievedChunk]:
        """Fuse multi-query results using Reciprocal Rank Fusion."""

        rrf_k = 60

        fused_scores: dict[str, float] = {}
        best_retrieval_scores: dict[str, float] = {}
        chunks_by_id: dict[str, RetrievedChunk] = {}

        for result in results:
            for rank, chunk in enumerate(
                result.chunks,
                start=1,
            ):
                chunk_id = chunk.chunk_id

                fused_scores[chunk_id] = (
                    fused_scores.get(
                        chunk_id,
                        0.0,
                    )
                    + 1.0 / (rrf_k + rank)
                )

                previous_score = (
                    best_retrieval_scores.get(
                        chunk_id
                    )
                )

                if (
                    previous_score is None
                    or chunk.score > previous_score
                ):
                    best_retrieval_scores[
                        chunk_id
                    ] = chunk.score

                    chunks_by_id[
                        chunk_id
                    ] = chunk

        ranked_chunk_ids = sorted(
            fused_scores,
            key=lambda chunk_id: (
                -fused_scores[chunk_id],
                -best_retrieval_scores[chunk_id],
                chunk_id,
            ),
        )

        return [
            chunks_by_id[chunk_id]
            for chunk_id in ranked_chunk_ids[
                : self.retry_evidence_limit
            ]
        ]