import pytest

from app.agents.supervisor import (
    SupervisorService,
    supervisor_node,
)
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
        content="Contenido de procedimiento.",
        score=0.9,
        metadata={
            "category": "restricted_areas",
        },
    )


def make_analysis() -> IncidentAnalysis:
    return IncidentAnalysis(
        severity="high",
        summary="Acceso no autorizado.",
        risks=[
            "Ingreso a sector restringido."
        ],
        recommended_escalation=(
            "Notificar a supervisión."
        ),
    )


def test_routes_to_procedure_agent_without_evidence() -> None:
    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="test-thread",
    )

    decision = SupervisorService().decide(
        state
    )

    assert decision.next_node == "procedure_agent"


def test_routes_to_incident_analyst_with_evidence() -> None:
    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="test-thread",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    decision = SupervisorService().decide(
        state
    )

    assert decision.next_node == "incident_analyst"


def test_routes_to_verification_after_analysis() -> None:
    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="test-thread",
    )

    state["retrieved_documents"] = [
        make_chunk()
    ]

    state["incident_analysis"] = (
        make_analysis()
    )

    decision = SupervisorService().decide(
        state
    )

    assert decision.next_node == "verification_agent"


def test_passed_verification_routes_to_response() -> None:
    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="test-thread",
    )

    state["verification_result"] = VerificationResult(
        status="passed",
        explanation="Evidence supports the analysis.",
        unsupported_claims=[],
        missing_information=[],
    )

    decision = SupervisorService().decide(
        state
    )

    assert decision.next_node == "response_composer"


def test_more_evidence_creates_cycle() -> None:
    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="test-thread",
    )

    state["retry_count"] = 1

    state["verification_result"] = VerificationResult(
        status="needs_more_evidence",
        explanation="More evidence is required.",
        unsupported_claims=[],
        missing_information=[
            "Authorization details"
        ],
    )

    decision = SupervisorService().decide(
        state
    )

    assert decision.next_node == "procedure_agent"


def test_retry_limit_routes_to_response() -> None:
    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="test-thread",
    )

    state["retry_count"] = 2

    state["verification_result"] = VerificationResult(
        status="needs_more_evidence",
        explanation="More evidence is required.",
        unsupported_claims=[],
        missing_information=[
            "Authorization details"
        ],
    )

    decision = SupervisorService().decide(
        state
    )

    assert decision.next_node == "response_composer"


@pytest.mark.asyncio
async def test_supervisor_node_updates_graph_state() -> None:
    state = create_initial_state(
        "persona sin autorizacion",
        thread_id="test-thread",
    )

    update = await supervisor_node(
        state
    )

    assert update["route"] == "procedure_agent"

    assert (
        update["agents_used"]
        == ["supervisor"]
    )

    assert update["supervisor_reason"]