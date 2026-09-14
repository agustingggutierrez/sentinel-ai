from typing import Protocol

from langchain_core.messages import AIMessage

from app.graph.state import SentinelState
from app.models.agents import IncidentAnalysis, VerificationResult
from app.models.retrieval import RetrievedChunk


class ResponseComposerPort(Protocol):
    """Interface required to compose the final user-facing response."""

    async def compose(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
        analysis: IncidentAnalysis,
        verification: VerificationResult,
    ) -> str:
        """Compose a grounded final answer."""


class ResponseComposerService:
    """Build the final answer from verified graph state."""

    def __init__(
        self,
        composer: ResponseComposerPort,
    ) -> None:
        self.composer = composer

    async def run(
        self,
        state: SentinelState,
    ) -> dict[str, object]:
        """Compose the final answer and update graph state."""

        evidence = state.get(
            "retrieved_documents",
            [],
        )

        if not evidence:
            raise ValueError(
                "Response Composer requires retrieved evidence."
            )

        analysis = state.get(
            "incident_analysis"
        )

        if analysis is None:
            raise ValueError(
                "Response Composer requires incident analysis."
            )

        verification = state.get(
            "verification_result"
        )

        if verification is None:
            raise ValueError(
                "Response Composer requires verification result."
            )

        answer = await self.composer.compose(
            query=state["query"],
            evidence=evidence,
            analysis=analysis,
            verification=verification,
        )

        normalized_answer = answer.strip()

        if not normalized_answer:
            raise ValueError(
                "Response Composer produced an empty answer."
            )

        agents_used = [
            *state.get(
                "agents_used",
                [],
            ),
            "response_composer",
        ]

        return {
            "final_answer": normalized_answer,
            "messages": [
                AIMessage(
                    content=normalized_answer,
                )
            ],
            "agents_used": agents_used,
        }