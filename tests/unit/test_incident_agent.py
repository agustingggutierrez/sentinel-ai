import pytest

from app.agents.incident import IncidentAnalystService
from app.graph.state import create_initial_state
from app.models.agents import IncidentAnalysis
from app.models.retrieval import RetrievedChunk


def make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        document_id="restricted-areas",
        title="Restricted Areas",
        chunk_id="restricted-areas::001::test",
        content=(
            "Toda persona dentro de un área restringida "
            "debe contar con autorización específica."
        ),
        score=0.92,
        metadata={
            "category": "restricted_areas",
            "section": "Autorización específica",
        },
    )


class FakeIncidentAnalyzer:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.evidence_batches: list[
            list[RetrievedChunk]
        ] = []

    async def analyze(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
    ) -> IncidentAnalysis:
        self.queries.append(query)
        self.evidence_batches.append(evidence)

        return IncidentAnalysis(
            severity="high",
            summary=(
                "Se detectó una persona sin autorización "
                "en un área restringida."
            ),
            risks=[
                "Acceso no autorizado",
                "Compromiso del área restringida",
            ],
            recommended_escalation=(
                "Notificar a supervisión y verificar "
                "la autorización de la persona."
            ),
        )


@pytest.mark.asyncio
async def test_incident_analyst_uses_query_and_evidence() -> None:
    analyzer = FakeIncidentAnalyzer()

    service = IncidentAnalystService(
        analyzer
    )

    state = create_initial_state(
        "persona sin autorizacion en area restringida",
        thread_id="incident-test",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    await service.run(
        state
    )

    assert analyzer.queries == [
        "persona sin autorizacion en area restringida"
    ]

    assert len(
        analyzer.evidence_batches
    ) == 1

    assert (
        analyzer.evidence_batches[0][0].document_id
        == "restricted-areas"
    )


@pytest.mark.asyncio
async def test_incident_analyst_returns_structured_analysis() -> None:
    service = IncidentAnalystService(
        FakeIncidentAnalyzer()
    )

    state = create_initial_state(
        "persona sin autorizacion en area restringida",
        thread_id="incident-test",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    update = await service.run(
        state
    )

    analysis = update[
        "incident_analysis"
    ]

    assert isinstance(
        analysis,
        IncidentAnalysis,
    )

    assert analysis.severity == "high"

    assert (
        "Acceso no autorizado"
        in analysis.risks
    )

    assert analysis.recommended_escalation


@pytest.mark.asyncio
async def test_incident_analyst_registers_itself() -> None:
    service = IncidentAnalystService(
        FakeIncidentAnalyzer()
    )

    state = create_initial_state(
        "consulta valida",
        thread_id="incident-test",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    state["agents_used"] = [
        "supervisor",
        "procedure_agent",
    ]

    update = await service.run(
        state
    )

    assert update["agents_used"] == [
        "supervisor",
        "procedure_agent",
        "incident_analyst",
    ]


@pytest.mark.asyncio
async def test_incident_analyst_requires_evidence() -> None:
    service = IncidentAnalystService(
        FakeIncidentAnalyzer()
    )

    state = create_initial_state(
        "consulta valida",
        thread_id="incident-test",
    )

    with pytest.raises(
        ValueError,
        match="requires retrieved evidence",
    ):
        await service.run(
            state
        )


@pytest.mark.asyncio
async def test_incident_analyst_does_not_replace_retrieved_documents() -> None:
    service = IncidentAnalystService(
        FakeIncidentAnalyzer()
    )

    state = create_initial_state(
        "consulta valida",
        thread_id="incident-test",
    )

    evidence = [
        make_chunk()
    ]

    state["retrieved_documents"] = evidence

    update = await service.run(
        state
    )

    assert (
        "retrieved_documents"
        not in update
    )

    assert (
        state["retrieved_documents"]
        == evidence
    )