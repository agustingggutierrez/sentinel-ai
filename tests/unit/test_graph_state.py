from uuid import UUID

import pytest
from langchain_core.messages import HumanMessage

from app.graph.state import SentinelState, create_initial_state


def test_initial_state_contains_expected_defaults() -> None:
    state = create_initial_state(
        "  acceso no autorizado  ",
        thread_id="thread-123",
    )

    assert isinstance(state, dict)
    assert state["query"] == "acceso no autorizado"
    assert state["thread_id"] == "thread-123"

    assert state["route"] is None
    assert state["supervisor_reason"] is None

    assert state["retrieved_documents"] == []
    assert state["sources"] == []

    assert state["incident_analysis"] is None
    assert state["verification_result"] is None

    assert state["retry_count"] == 0
    assert state["agents_used"] == []

    assert state["final_answer"] is None
    assert state["trace_id"] is None


def test_initial_state_contains_human_message() -> None:
    state = create_initial_state(
        "persona en area restringida",
        thread_id="thread-456",
    )

    messages = state["messages"]

    assert len(messages) == 1
    assert isinstance(
        messages[0],
        HumanMessage,
    )
    assert (
        messages[0].content
        == "persona en area restringida"
    )


def test_thread_id_is_generated_when_missing() -> None:
    state = create_initial_state(
        "consulta valida"
    )

    generated_thread_id = state["thread_id"]

    parsed_uuid = UUID(
        generated_thread_id
    )

    assert str(parsed_uuid) == generated_thread_id


def test_blank_thread_id_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="thread_id cannot be blank",
    ):
        create_initial_state(
            "consulta valida",
            thread_id="   ",
        )


def test_invalid_query_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="at least 3 characters",
    ):
        create_initial_state(
            "  "
        )


def test_sentinel_state_type_is_available() -> None:
    assert SentinelState is not None

@pytest.mark.asyncio
async def test_message_reducer_appends_graph_messages() -> None:
    from langchain_core.messages import AIMessage
    from langgraph.graph import END, START, StateGraph

    async def test_node(
        state: SentinelState,
    ) -> dict[str, object]:
        return {
            "messages": [
                AIMessage(
                    content=f"Procesado: {state['query']}"
                )
            ]
        }

    builder = StateGraph(
        SentinelState
    )

    builder.add_node(
        "test_node",
        test_node,
    )

    builder.add_edge(
        START,
        "test_node",
    )

    builder.add_edge(
        "test_node",
        END,
    )

    graph = builder.compile()

    initial_state = create_initial_state(
        "consulta de seguridad",
        thread_id="graph-test",
    )

    result = await graph.ainvoke(
        initial_state
    )

    assert len(result["messages"]) == 2

    assert isinstance(
        result["messages"][0],
        HumanMessage,
    )

    assert isinstance(
        result["messages"][1],
        AIMessage,
    )

    assert (
        result["messages"][1].content
        == "Procesado: consulta de seguridad"
    )
