import pytest
from langchain_core.messages import AIMessage

from app.agents.response import ResponseComposerService
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
        score=0.94,
        metadata={
            "category": "restricted_areas",
            "section": "Autorización específica",
        },
    )


def make_analysis() -> IncidentAnalysis:
    return IncidentAnalysis(
        severity="high",
        summary=(
            "Se detectó un posible acceso no autorizado."
        ),
        risks=[
            "Acceso a sector restringido",
        ],
        recommended_escalation=(
            "Notificar a supervisión y validar autorización."
        ),
    )


def make_verification() -> VerificationResult:
    return VerificationResult(
        status="passed",
        explanation=(
            "El análisis está respaldado por la evidencia."
        ),
        unsupported_claims=[],
        missing_information=[],
    )


class FakeComposer:
    def __init__(
        self,
        answer: str = (
            "Debe verificarse la autorización y notificarse "
            "a supervisión."
        ),
    ) -> None:
        self.answer = answer
        self.calls = []

    async def compose(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
        analysis: IncidentAnalysis,
        verification: VerificationResult,
    ) -> str:
        self.calls.append(
            (
                query,
                evidence,
                analysis,
                verification,
            )
        )

        return self.answer


@pytest.mark.asyncio
async def test_response_composer_uses_complete_state() -> None:
    composer = FakeComposer()

    service = ResponseComposerService(
        composer
    )

    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="response-test",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    state["incident_analysis"] = (
        make_analysis()
    )

    state["verification_result"] = (
        make_verification()
    )

    await service.run(
        state
    )

    assert len(composer.calls) == 1

    (
        query,
        evidence,
        analysis,
        verification,
    ) = composer.calls[0]

    assert query == "persona sin autorizacion"
    assert evidence[0].document_id == "restricted-areas"
    assert analysis.severity == "high"
    assert verification.status == "passed"


@pytest.mark.asyncio
async def test_response_composer_returns_final_answer() -> None:
    service = ResponseComposerService(
        FakeComposer()
    )

    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="response-test",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    state["incident_analysis"] = (
        make_analysis()
    )

    state["verification_result"] = (
        make_verification()
    )

    update = await service.run(
        state
    )

    assert update["final_answer"] == (
        "Debe verificarse la autorización y notificarse "
        "a supervisión."
    )


@pytest.mark.asyncio
async def test_response_composer_appends_ai_message() -> None:
    service = ResponseComposerService(
        FakeComposer()
    )

    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="response-test",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    state["incident_analysis"] = (
        make_analysis()
    )

    state["verification_result"] = (
        make_verification()
    )

    update = await service.run(
        state
    )

    messages = update[
        "messages"
    ]

    assert len(messages) == 1

    assert isinstance(
        messages[0],
        AIMessage,
    )

    assert messages[0].content


@pytest.mark.asyncio
async def test_response_composer_registers_itself() -> None:
    service = ResponseComposerService(
        FakeComposer()
    )

    state = create_initial_state(
        "consulta valida",
        thread_id="response-test",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    state["incident_analysis"] = (
        make_analysis()
    )

    state["verification_result"] = (
        make_verification()
    )

    state["agents_used"] = [
        "supervisor",
        "procedure_agent",
        "incident_analyst",
        "verification_agent",
    ]

    update = await service.run(
        state
    )

    assert update["agents_used"] == [
        "supervisor",
        "procedure_agent",
        "incident_analyst",
        "verification_agent",
        "response_composer",
    ]


@pytest.mark.asyncio
async def test_response_composer_requires_complete_state() -> None:
    service = ResponseComposerService(
        FakeComposer()
    )

    state = create_initial_state(
        "consulta valida",
        thread_id="response-test",
    )

    with pytest.raises(
        ValueError,
        match="requires retrieved evidence",
    ):
        await service.run(
            state
        )


@pytest.mark.asyncio
async def test_response_composer_rejects_empty_answer() -> None:
    service = ResponseComposerService(
        FakeComposer(
            answer="   "
        )
    )

    state = create_initial_state(
        "consulta valida",
        thread_id="response-test",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    state["incident_analysis"] = (
        make_analysis()
    )

    state["verification_result"] = (
        make_verification()
    )

    with pytest.raises(
        ValueError,
        match="produced an empty answer",
    ):
        await service.run(
            state
        )