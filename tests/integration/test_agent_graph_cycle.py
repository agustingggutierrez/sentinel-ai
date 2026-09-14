import pytest

from app.agents.incident import IncidentAnalystService
from app.agents.procedure import ProcedureAgentService
from app.agents.response import ResponseComposerService
from app.agents.verification import VerificationAgentService
from app.graph.state import create_initial_state
from app.graph.workflow import build_sentinel_graph
from app.models.agents import IncidentAnalysis, VerificationResult
from app.models.retrieval import RetrievalResult, RetrievedChunk


def make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        document_id="restricted-areas",
        title="Restricted Areas",
        chunk_id="restricted-areas::001::cycle",
        content=(
            "Toda persona en un área restringida "
            "debe contar con autorización específica."
        ),
        score=0.96,
        metadata={
            "category": "restricted_areas",
            "section": "Autorización específica",
        },
    )


class TrackingRetrieval:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def retrieve(
        self,
        query: str,
        *,
        category: str | None = None,
        priority: str | None = None,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> RetrievalResult:
        self.queries.append(query)

        return RetrievalResult(
            query=query,
            chunks=[
                make_chunk()
            ],
            total_found=1,
        )


class TrackingAnalyzer:
    def __init__(self) -> None:
        self.call_count = 0

    async def analyze(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
    ) -> IncidentAnalysis:
        self.call_count += 1

        return IncidentAnalysis(
            severity="high",
            summary=(
                "Existe un posible acceso no autorizado "
                "a un área restringida."
            ),
            risks=[
                "Acceso no autorizado",
            ],
            recommended_escalation=(
                "Verificar autorización y notificar "
                "a supervisión."
            ),
        )


class RetryThenPassVerifier:
    def __init__(self) -> None:
        self.call_count = 0

    async def verify(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
        analysis: IncidentAnalysis,
    ) -> VerificationResult:
        self.call_count += 1

        if self.call_count == 1:
            return VerificationResult(
                status="needs_more_evidence",
                explanation=(
                    "La autorización del técnico "
                    "todavía no está confirmada."
                ),
                unsupported_claims=[
                    "El técnico no posee autorización.",
                ],
                missing_information=[
                    "Confirmar autorización vigente del técnico",
                ],
            )

        return VerificationResult(
            status="passed",
            explanation=(
                "La evidencia adicional permite "
                "respaldar el análisis."
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
            "Verifique la autorización vigente del técnico "
            "y notifique la situación a supervisión."
        )


@pytest.mark.asyncio
async def test_graph_retries_when_verification_needs_more_evidence() -> None:
    retrieval = TrackingRetrieval()
    analyzer = TrackingAnalyzer()
    verifier = RetryThenPassVerifier()

    graph = build_sentinel_graph(
        procedure_agent=ProcedureAgentService(
            retrieval
        ),
        incident_analyst=IncidentAnalystService(
            analyzer
        ),
        verification_agent=VerificationAgentService(
            verifier
        ),
        response_composer=ResponseComposerService(
            FakeComposer()
        ),
    )

    state = create_initial_state(
        "un tecnico ingreso a un area restringida",
        thread_id="cycle-integration",
    )

    result = await graph.ainvoke(
        state
    )

    assert len(retrieval.queries) == 2

    assert retrieval.queries[0] == (
        "un tecnico ingreso a un area restringida"
    )

    assert (
        "Confirmar autorización vigente del técnico"
        in retrieval.queries[1]
    )

    assert analyzer.call_count == 2
    assert verifier.call_count == 2

    assert result["retry_count"] == 1

    assert (
        result["verification_result"].status
        == "passed"
    )

    assert result["final_answer"] == (
        "Verifique la autorización vigente del técnico "
        "y notifique la situación a supervisión."
    )

    assert result["agents_used"] == [
        "supervisor",
        "procedure_agent",
        "supervisor",
        "incident_analyst",
        "supervisor",
        "verification_agent",
        "supervisor",
        "procedure_agent",
        "supervisor",
        "incident_analyst",
        "supervisor",
        "verification_agent",
        "supervisor",
        "response_composer",
    ]