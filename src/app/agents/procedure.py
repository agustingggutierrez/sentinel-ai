from typing import Protocol

from app.graph.state import SentinelState
from app.models.response import SourceReference
from app.models.retrieval import RetrievalResult


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
    ) -> None:
        self.retrieval_service = retrieval_service

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

        retrieval_query = query

        if (
            is_retry
            and verification.missing_information
        ):
            missing_information = "; ".join(
                verification.missing_information
            )

            retrieval_query = (
                f"{query}\n\n"
                "Información adicional que debe verificarse: "
                f"{missing_information}"
            )

        result = await self.retrieval_service.retrieve(
            retrieval_query
        )

        sources = [
            SourceReference(
                document_id=chunk.document_id,
                title=chunk.title,
                chunk_id=chunk.chunk_id,
                score=chunk.score,
            )
            for chunk in result.chunks
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
            "retrieved_documents": result.chunks,
            "sources": sources,
            "retry_count": retry_count,
            "agents_used": agents_used,
        }

        if is_retry:
            update["verification_result"] = None
            update["incident_analysis"] = None

        return update