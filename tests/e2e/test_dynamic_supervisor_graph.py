import pytest

from app.graph.state import create_initial_state
from app.graph.workflow import build_sentinel_graph
from app.models.agents import SupervisorDecision


class FakeDynamicSupervisor:
    def __init__(self) -> None:
        self.call_count = 0

    async def decide(
        self,
        state,
    ) -> SupervisorDecision:
        self.call_count += 1

        return SupervisorDecision(
            next_node="finish",
            reason=(
                "A final answer already exists, "
                "so the graph can finish."
            ),
        )


class NeverCalledService:
    async def run(
        self,
        state,
    ):
        raise AssertionError(
            "Specialized agent should not have been called."
        )


@pytest.mark.asyncio
async def test_graph_uses_injected_dynamic_supervisor() -> None:
    supervisor = FakeDynamicSupervisor()

    graph = build_sentinel_graph(
        procedure_agent=NeverCalledService(),
        incident_analyst=NeverCalledService(),
        verification_agent=NeverCalledService(),
        response_composer=NeverCalledService(),
        supervisor=supervisor,
    )

    state = create_initial_state(
        "consulta ya resuelta",
        thread_id="dynamic-supervisor-test",
    )

    state["final_answer"] = (
        "Respuesta existente."
    )

    result = await graph.ainvoke(
        state
    )

    assert supervisor.call_count == 1

    assert result["route"] == "finish"

    assert result["final_answer"] == (
        "Respuesta existente."
    )

    assert result["agents_used"] == [
        "supervisor",
    ]

    assert (
        "graph can finish"
        in result["supervisor_reason"]
    )