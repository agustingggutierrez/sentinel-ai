import pytest

from app.agents.verification import VerificationAgentService
from app.graph.state import create_initial_state
from app.models.agents import (
    IncidentAnalysis,
    VerificationResult,
)
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
        score=0.93,
        metadata={
            "category": "restricted_areas",
            "section": "Autorización específica",
        },
    )


def make_analysis() -> IncidentAnalysis:
    return IncidentAnalysis(
        severity="high",
        summary=(
            "Se detectó una persona sin autorización "
            "en un área restringida."
        ),
        risks=[
            "Acceso no autorizado",
        ],
        recommended_escalation=(
            "Notificar a supervisión."
        ),
    )


class FakeVerifier:
    def __init__(
        self,
        result: VerificationResult,
    ) -> None:
        self.result = result
        self.calls: list[
            tuple[
                str,
                list[RetrievedChunk],
                IncidentAnalysis,
            ]
        ] = []

    async def verify(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
        analysis: IncidentAnalysis,
    ) -> VerificationResult:
        self.calls.append(
            (
                query,
                evidence,
                analysis,
            )
        )

        return self.result


def passed_result() -> VerificationResult:
    return VerificationResult(
        status="passed",
        explanation=(
            "El análisis está respaldado por la evidencia."
        ),
        unsupported_claims=[],
        missing_information=[],
    )


@pytest.mark.asyncio
async def test_verification_agent_uses_query_evidence_and_analysis() -> None:
    verifier = FakeVerifier(
        passed_result()
    )

    service = VerificationAgentService(
        verifier
    )

    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="verification-test",
    )

    evidence = [
        make_chunk()
    ]

    analysis = make_analysis()

    state["retrieved_documents"] = evidence
    state["incident_analysis"] = analysis

    await service.run(
        state
    )

    assert len(verifier.calls) == 1

    query, used_evidence, used_analysis = (
        verifier.calls[0]
    )

    assert query == "persona sin autorizacion"
    assert used_evidence == evidence
    assert used_analysis == analysis


@pytest.mark.asyncio
async def test_verification_agent_returns_structured_result() -> None:
    service = VerificationAgentService(
        FakeVerifier(
            passed_result()
        )
    )

    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="verification-test",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    state["incident_analysis"] = (
        make_analysis()
    )

    update = await service.run(
        state
    )

    result = update[
        "verification_result"
    ]

    assert isinstance(
        result,
        VerificationResult,
    )

    assert result.status == "passed"
    assert result.unsupported_claims == []
    assert result.missing_information == []


@pytest.mark.asyncio
async def test_verification_agent_supports_more_evidence_result() -> None:
    result = VerificationResult(
        status="needs_more_evidence",
        explanation=(
            "No se puede confirmar la autorización."
        ),
        unsupported_claims=[
            "La persona carece de autorización."
        ],
        missing_information=[
            "Confirmar autorización vigente",
        ],
    )

    service = VerificationAgentService(
        FakeVerifier(
            result
        )
    )

    state = create_initial_state(
        "persona en area restringida",
        thread_id="verification-test",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    state["incident_analysis"] = (
        make_analysis()
    )

    update = await service.run(
        state
    )

    verification = update[
        "verification_result"
    ]

    assert (
        verification.status
        == "needs_more_evidence"
    )

    assert verification.missing_information == [
        "Confirmar autorización vigente",
    ]


@pytest.mark.asyncio
async def test_verification_agent_registers_itself() -> None:
    service = VerificationAgentService(
        FakeVerifier(
            passed_result()
        )
    )

    state = create_initial_state(
        "consulta valida",
        thread_id="verification-test",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    state["incident_analysis"] = (
        make_analysis()
    )

    state["agents_used"] = [
        "supervisor",
        "procedure_agent",
        "incident_analyst",
    ]

    update = await service.run(
        state
    )

    assert update["agents_used"] == [
        "supervisor",
        "procedure_agent",
        "incident_analyst",
        "verification_agent",
    ]


@pytest.mark.asyncio
async def test_verification_agent_requires_evidence() -> None:
    service = VerificationAgentService(
        FakeVerifier(
            passed_result()
        )
    )

    state = create_initial_state(
        "consulta valida",
        thread_id="verification-test",
    )

    state["incident_analysis"] = (
        make_analysis()
    )

    with pytest.raises(
        ValueError,
        match="requires retrieved evidence",
    ):
        await service.run(
            state
        )


@pytest.mark.asyncio
async def test_verification_agent_requires_analysis() -> None:
    service = VerificationAgentService(
        FakeVerifier(
            passed_result()
        )
    )

    state = create_initial_state(
        "consulta valida",
        thread_id="verification-test",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    with pytest.raises(
        ValueError,
        match="requires incident analysis",
    ):
        await service.run(
            state
        )