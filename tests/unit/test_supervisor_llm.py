import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.state import create_initial_state
from app.models.agents import (
    IncidentAnalysis,
    SupervisorDecision,
    VerificationResult,
)
from app.models.retrieval import RetrievedChunk
from app.services.supervisor_llm import OpenAISupervisor


def make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        document_id="restricted-areas",
        title="Restricted Areas",
        chunk_id="restricted-areas::002::authorization",
        content="Toda persona requiere autorización específica.",
        score=0.94,
        metadata={
            "section": "Autorización específica",
        },
    )


class FakeStructuredModel:
    def __init__(
        self,
        result: object,
    ) -> None:
        self.result = result
        self.inputs: list[object] = []

    async def ainvoke(
        self,
        input: object,
    ) -> object:
        self.inputs.append(input)
        return self.result


class FakeFactory:
    def __init__(
        self,
        model: FakeStructuredModel,
    ) -> None:
        self.model = model
        self.schemas: list[type[SupervisorDecision]] = []

    def create_structured_model(
        self,
        schema: type[SupervisorDecision],
    ) -> FakeStructuredModel:
        self.schemas.append(schema)
        return self.model


def make_decision() -> SupervisorDecision:
    return SupervisorDecision(
        next_node="procedure_agent",
        reason="No procedural evidence is available yet.",
    )


def test_supervisor_requests_structured_decision_schema() -> None:
    factory = FakeFactory(
        FakeStructuredModel(
            make_decision()
        )
    )

    OpenAISupervisor(
        factory
    )

    assert factory.schemas == [
        SupervisorDecision
    ]


@pytest.mark.asyncio
async def test_supervisor_returns_structured_decision() -> None:
    supervisor = OpenAISupervisor(
        FakeFactory(
            FakeStructuredModel(
                make_decision()
            )
        )
    )

    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="supervisor-llm-test",
    )

    result = await supervisor.decide(
        state
    )

    assert isinstance(
        result,
        SupervisorDecision,
    )

    assert result.next_node == "procedure_agent"
    assert result.reason


@pytest.mark.asyncio
async def test_supervisor_receives_routing_relevant_state() -> None:
    model = FakeStructuredModel(
        SupervisorDecision(
            next_node="verification_agent",
            reason="Analysis requires verification.",
        )
    )

    supervisor = OpenAISupervisor(
        FakeFactory(
            model
        )
    )

    state = create_initial_state(
        "tecnico dentro de area restringida",
        thread_id="supervisor-llm-test",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    state["incident_analysis"] = IncidentAnalysis(
        severity="high",
        summary="Posible acceso no autorizado.",
        risks=[
            "Acceso a sector restringido",
        ],
        recommended_escalation=(
            "Validar autorización."
        ),
    )

    state["retry_count"] = 1

    await supervisor.decide(
        state
    )

    assert len(model.inputs) == 1

    messages = model.inputs[0]

    assert isinstance(
        messages,
        list,
    )

    assert isinstance(
        messages[0],
        SystemMessage,
    )

    assert isinstance(
        messages[1],
        HumanMessage,
    )

    content = str(
        messages[1].content
    )

    assert (
        "tecnico dentro de area restringida"
        in content
    )

    assert "retrieved_document_count: 1" in content
    assert "restricted-areas" in content
    assert "incident_analysis: present" in content
    assert "verification_status: not_run" in content
    assert "retry_count: 1" in content
    assert "final_answer: missing" in content


@pytest.mark.asyncio
async def test_supervisor_receives_verification_status() -> None:
    model = FakeStructuredModel(
        SupervisorDecision(
            next_node="procedure_agent",
            reason="More evidence is required.",
        )
    )

    supervisor = OpenAISupervisor(
        FakeFactory(
            model
        )
    )

    state = create_initial_state(
        "consulta valida",
        thread_id="supervisor-llm-test",
    )

    state["verification_result"] = VerificationResult(
        status="needs_more_evidence",
        explanation="Falta confirmar autorización.",
        unsupported_claims=[],
        missing_information=[
            "Autorización vigente",
        ],
    )

    await supervisor.decide(
        state
    )

    messages = model.inputs[0]
    content = str(
        messages[1].content
    )

    assert (
        "verification_status: needs_more_evidence"
        in content
    )


@pytest.mark.asyncio
async def test_supervisor_rejects_unexpected_model_output() -> None:
    supervisor = OpenAISupervisor(
        FakeFactory(
            FakeStructuredModel(
                {
                    "next_node": "procedure_agent",
                }
            )
        )
    )

    state = create_initial_state(
        "consulta valida",
        thread_id="supervisor-llm-test",
    )

    with pytest.raises(
        TypeError,
        match="did not return SupervisorDecision",
    ):
        await supervisor.decide(
            state
        )

@pytest.mark.asyncio
async def test_supervisor_prompt_includes_safe_response_routing() -> None:
    model = FakeStructuredModel(
        SupervisorDecision(
            next_node="safe_response",
            reason="Verification failed.",
        )
    )

    supervisor = OpenAISupervisor(
        FakeFactory(
            model
        )
    )

    state = create_initial_state(
        "consulta valida",
        thread_id="supervisor-safe-routing-test",
    )

    state["verification_result"] = VerificationResult(
        status="failed",
        explanation="La evidencia no respalda el analisis.",
        unsupported_claims=[
            "Severidad no confirmada.",
        ],
        missing_information=[],
    )

    await supervisor.decide(
        state
    )

    messages = model.inputs[0]

    assert isinstance(
        messages,
        list,
    )

    system_message = messages[0]

    assert isinstance(
        system_message,
        SystemMessage,
    )

    content = str(
        system_message.content
    )

    assert (
        "Use response_composer only when verification status is "
        "'passed'"
        in content
    )

    assert (
        "Use safe_response when verification status is 'failed'"
        in content
    )

    assert (
        "use safe_response when verification still requires "
        "more evidence but the retry limit has been reached"
        in content
    )
