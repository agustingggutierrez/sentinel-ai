import pytest

from app.agents.incident import IncidentAnalystService
from app.agents.procedure import ProcedureAgentService
from app.agents.response import ResponseComposerService
from app.agents.verification import VerificationAgentService
from app.graph.state import create_initial_state
from app.graph.workflow import build_sentinel_graph
from app.models.agents import (
    IncidentAnalysis,
    VerificationResult,
)
from app.models.retrieval import RetrievalResult, RetrievedChunk


def make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        document_id="restricted-areas",
        title="Restricted Areas",
        chunk_id="restricted-areas::001::graph",
        content=(
            "Toda persona en un área restringida "
            "debe contar con autorización específica."
        ),
        score=0.95,
        metadata={
            "category": "restricted_areas",
            "section": "Autorización específica",
        },
    )


class FakeRetrieval:
    async def retrieve(
        self,
        query: str,
        *,
        category: str | None = None,
        priority: str | None = None,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> RetrievalResult:
        return RetrievalResult(
            query=query,
            chunks=[
                make_chunk()
            ],
            total_found=1,
        )


class FakeAnalyzer:
    async def analyze(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
    ) -> IncidentAnalysis:
        return IncidentAnalysis(
            severity="high",
            summary=(
                "Posible acceso no autorizado "
                "a un área restringida."
            ),
            risks=[
                "Acceso no autorizado",
            ],
            recommended_escalation=(
                "Validar autorización y notificar "
                "a supervisión."
            ),
        )


class FakeVerifier:
    async def verify(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
        analysis: IncidentAnalysis,
    ) -> VerificationResult:
        return VerificationResult(
            status="passed",
            explanation=(
                "La evidencia respalda el análisis."
            ),
            unsupported_claims=[],
            missing_information=[],
        )


class FakeComposer:
    async def compose(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
        analysis: IncidentAnalysis,
        verification: VerificationResult,
    ) -> str:
        return (
            "Verifique la autorización de la persona "
            "y notifique a supervisión."
        )


@pytest.mark.asyncio
async def test_complete_multi_agent_graph() -> None:
    graph = build_sentinel_graph(
        procedure_agent=ProcedureAgentService(
            FakeRetrieval()
        ),
        incident_analyst=IncidentAnalystService(
            FakeAnalyzer()
        ),
        verification_agent=VerificationAgentService(
            FakeVerifier()
        ),
        response_composer=ResponseComposerService(
            FakeComposer()
        ),
    )

    state = create_initial_state(
        "persona sin autorizacion en area restringida",
        thread_id="graph-integration",
    )

    result = await graph.ainvoke(
        state
    )

    assert result["final_answer"] == (
        "Verifique la autorización de la persona "
        "y notifique a supervisión."
    )

    assert (
        result["verification_result"].status
        == "passed"
    )

    assert (
        result["incident_analysis"].severity
        == "high"
    )

    assert len(
        result["retrieved_documents"]
    ) == 1

    assert result["agents_used"] == [
        "supervisor",
        "procedure_agent",
        "supervisor",
        "incident_analyst",
        "supervisor",
        "verification_agent",
        "supervisor",
        "response_composer",
    ]

    assert len(
        result["messages"]
    ) == 2