import pytest

from app.agents.procedure import ProcedureAgentService
from app.graph.state import create_initial_state
from app.models.agents import (
    IncidentAnalysis,
    VerificationResult,
)
from app.models.retrieval import RetrievalResult, RetrievedChunk


class FakeRetrievalService:
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

        chunk = RetrievedChunk(
            document_id="restricted-areas",
            title="Restricted Areas",
            chunk_id="restricted-areas::001::test",
            content="Procedimiento operativo relevante.",
            score=0.91,
            metadata={
                "category": "restricted_areas",
                "section": "Acceso no autorizado",
            },
        )

        return RetrievalResult(
            query=query,
            chunks=[chunk],
            total_found=1,
        )


@pytest.mark.asyncio
async def test_procedure_agent_retrieves_evidence() -> None:
    retrieval = FakeRetrievalService()

    service = ProcedureAgentService(
        retrieval
    )

    state = create_initial_state(
        "persona en area restringida",
        thread_id="procedure-test",
    )

    update = await service.run(
        state
    )

    assert len(
        update["retrieved_documents"]
    ) == 1

    chunk = update[
        "retrieved_documents"
    ][0]

    assert chunk.document_id == "restricted-areas"

    assert retrieval.queries == [
        "persona en area restringida"
    ]


@pytest.mark.asyncio
async def test_procedure_agent_builds_sources() -> None:
    service = ProcedureAgentService(
        FakeRetrievalService()
    )

    state = create_initial_state(
        "persona en area restringida",
        thread_id="procedure-test",
    )

    update = await service.run(
        state
    )

    sources = update["sources"]

    assert len(sources) == 1
    assert sources[0].document_id == "restricted-areas"
    assert sources[0].chunk_id == "restricted-areas::001::test"
    assert sources[0].score == pytest.approx(0.91)


@pytest.mark.asyncio
async def test_procedure_agent_registers_itself() -> None:
    service = ProcedureAgentService(
        FakeRetrievalService()
    )

    state = create_initial_state(
        "consulta valida",
        thread_id="procedure-test",
    )

    state["agents_used"] = [
        "supervisor"
    ]

    update = await service.run(
        state
    )

    assert update["agents_used"] == [
        "supervisor",
        "procedure_agent",
    ]


@pytest.mark.asyncio
async def test_retry_uses_independent_retrieval_queries() -> None:
    retrieval = FakeRetrievalService()

    service = ProcedureAgentService(
        retrieval
    )

    state = create_initial_state(
        "persona en area restringida",
        thread_id="procedure-test",
    )

    state["verification_result"] = VerificationResult(
        status="needs_more_evidence",
        explanation="Falta informacion.",
        unsupported_claims=[],
        missing_information=[
            "Buscar politica de severidad",
            "Buscar procedimiento de escalamiento",
        ],
    )

    update = await service.run(
        state
    )

    assert len(retrieval.queries) == 3

    assert set(retrieval.queries) == {
        "persona en area restringida",
        "Buscar politica de severidad",
        "Buscar procedimiento de escalamiento",
    }

    assert update["retry_count"] == 1


@pytest.mark.asyncio
async def test_retry_deduplicates_retrieved_evidence() -> None:
    retrieval = FakeRetrievalService()

    service = ProcedureAgentService(
        retrieval
    )

    state = create_initial_state(
        "persona en area restringida",
        thread_id="procedure-test",
    )

    state["verification_result"] = VerificationResult(
        status="needs_more_evidence",
        explanation="Falta informacion.",
        unsupported_claims=[],
        missing_information=[
            "Buscar severidad",
            "Buscar escalamiento",
            "Buscar registro",
        ],
    )

    update = await service.run(
        state
    )

    retrieved_documents = update[
        "retrieved_documents"
    ]

    sources = update["sources"]

    assert len(retrieved_documents) == 1
    assert len(sources) == 1

    assert (
        retrieved_documents[0].chunk_id
        == "restricted-areas::001::test"
    )


@pytest.mark.asyncio
async def test_retry_clears_stale_analysis_and_verification() -> None:
    service = ProcedureAgentService(
        FakeRetrievalService()
    )

    state = create_initial_state(
        "persona en area restringida",
        thread_id="procedure-test",
    )

    state["incident_analysis"] = IncidentAnalysis(
        severity="high",
        summary="Analisis anterior.",
        risks=[
            "Riesgo previo."
        ],
        recommended_escalation=(
            "Escalamiento anterior."
        ),
    )

    state["verification_result"] = VerificationResult(
        status="needs_more_evidence",
        explanation="Faltan datos.",
        unsupported_claims=[],
        missing_information=[
            "Identidad de la persona"
        ],
    )

    update = await service.run(
        state
    )

    assert update["incident_analysis"] is None
    assert update["verification_result"] is None
    assert update["retry_count"] == 1


def test_procedure_agent_rejects_invalid_retry_limit() -> None:
    with pytest.raises(
        ValueError,
        match="retry_evidence_limit must be at least 1",
    ):
        ProcedureAgentService(
            FakeRetrievalService(),
            retry_evidence_limit=0,
        )