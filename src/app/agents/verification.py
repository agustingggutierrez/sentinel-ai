from typing import Protocol

from app.graph.state import SentinelState
from app.models.agents import (
    IncidentAnalysis,
    VerificationResult,
)
from app.models.retrieval import RetrievedChunk


class VerificationPort(Protocol):
    """Structured verification interface required by the agent."""

    async def verify(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
        analysis: IncidentAnalysis,
    ) -> VerificationResult:
        """Verify whether the analysis is supported by evidence."""


class VerificationAgentService:
    """Verify incident analysis against retrieved evidence."""

    def __init__(
        self,
        verifier: VerificationPort,
    ) -> None:
        self.verifier = verifier

    async def run(
        self,
        state: SentinelState,
    ) -> dict[str, object]:
        """Verify the current analysis and update graph state."""

        evidence = state.get(
            "retrieved_documents",
            [],
        )

        if not evidence:
            raise ValueError(
                "Verification Agent requires retrieved evidence."
            )

        analysis = state.get(
            "incident_analysis"
        )

        if analysis is None:
            raise ValueError(
                "Verification Agent requires incident analysis."
            )

        result = await self.verifier.verify(
            query=state["query"],
            evidence=evidence,
            analysis=analysis,
        )

        agents_used = [
            *state.get(
                "agents_used",
                [],
            ),
            "verification_agent",
        ]

        return {
            "verification_result": result,
            "agents_used": agents_used,
        }