from typing import Protocol

from app.graph.state import SentinelState
from app.models.agents import IncidentAnalysis
from app.models.retrieval import RetrievedChunk


class IncidentAnalysisPort(Protocol):
    """Structured analysis interface required by the Incident Analyst."""

    async def analyze(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
    ) -> IncidentAnalysis:
        """Analyze an incident using the available evidence."""


class IncidentAnalystService:
    """Coordinate structured incident analysis for the graph."""

    def __init__(
        self,
        analyzer: IncidentAnalysisPort,
    ) -> None:
        self.analyzer = analyzer

    async def run(
        self,
        state: SentinelState,
    ) -> dict[str, object]:
        """Analyze the incident and update the shared graph state."""

        query = state["query"]

        evidence = state.get(
            "retrieved_documents",
            [],
        )

        if not evidence:
            raise ValueError(
                "Incident Analyst requires retrieved evidence."
            )

        analysis = await self.analyzer.analyze(
            query=query,
            evidence=evidence,
        )

        agents_used = [
            *state.get(
                "agents_used",
                [],
            ),
            "incident_analyst",
        ]

        return {
            "incident_analysis": analysis,
            "agents_used": agents_used,
        }