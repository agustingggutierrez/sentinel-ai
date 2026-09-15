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
        chunk = RetrievedChunk(
            document_id="restricted-areas",
            title="Restricted Areas",
            chunk_id="restricted-areas::001::test",
            content=(
                "El acceso a un area restringida requiere "
                "autorizacion especifica."
            ),
            score=0.95,
            metadata={
                "section": "Autorizacion especifica",
            },
        )

        return RetrievalResult(
            query=query,
            chunks=[chunk],
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
            summary="Intento de acceso no autorizado.",
            risks=[
                "Riesgo no confirmado.",
            ],
            recommended_escalation=(
                "Escalamiento no confirmado."
            ),
        )


class FailedVerifier:
    async def verify(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
        analysis: IncidentAnalysis,
    ) -> VerificationResult:
        return VerificationResult(
            status="failed",
            explanation=(
                "La evidencia no respalda la severidad "
                "ni el escalamiento propuesto."
            ),
            unsupported_claims=[
                "Severidad alta.",
                "Escalamiento obligatorio.",
            ],
            missing_information=[],
        )


class TrackingComposer:
    def __init__(self) -> None:
        self.call_count = 0

    async def compose(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
        analysis: IncidentAnalysis,
        verification: VerificationResult,
    ) -> str:
        self.call_count += 1

        return "Esta respuesta no deberia ejecutarse."


@pytest.mark.asyncio
async def test_failed_verification_uses_safe_response() -> None:
    composer = TrackingComposer()

    graph = build_sentinel_graph(
        procedure_agent=ProcedureAgentService(
            FakeRetrieval()
        ),
        incident_analyst=IncidentAnalystService(
            FakeAnalyzer()
        ),
        verification_agent=VerificationAgentService(
            FailedVerifier()
        ),
        response_composer=ResponseComposerService(
            composer
        ),
    )

    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="safe-response-test",
    )

    result = await graph.ainvoke(
        state
    )

    assert composer.call_count == 0

    assert (
        result["verification_result"].status
        == "failed"
    )

    assert result["agents_used"][-1] == "safe_response"

    assert (
        "No hay evidencia suficiente"
        in result["final_answer"]
    )

    assert (
        "Severidad alta."
        in result["final_answer"]
    )

    assert (
        "Escalamiento obligatorio."
        in result["final_answer"]
    )