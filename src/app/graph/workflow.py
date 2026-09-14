from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.incident import IncidentAnalystService
from app.agents.procedure import ProcedureAgentService
from app.agents.response import ResponseComposerService
from app.agents.supervisor import supervisor_node
from app.agents.verification import VerificationAgentService
from app.graph.state import SentinelState
from app.models.agents import AgentRoute


def route_from_supervisor(
    state: SentinelState,
) -> AgentRoute:
    """Return the node selected by the Supervisor."""

    route = state.get(
        "route"
    )

    if route is None:
        raise RuntimeError(
            "Supervisor did not define a graph route."
        )

    return route


def build_sentinel_graph(
    *,
    procedure_agent: ProcedureAgentService,
    incident_analyst: IncidentAnalystService,
    verification_agent: VerificationAgentService,
    response_composer: ResponseComposerService,
    checkpointer: Any | None = None,
) -> Any:
    """Build and compile the SentinelAI multi-agent LangGraph."""

    async def procedure_node(
        state: SentinelState,
    ) -> dict[str, object]:
        return await procedure_agent.run(
            state
        )

    async def incident_node(
        state: SentinelState,
    ) -> dict[str, object]:
        return await incident_analyst.run(
            state
        )

    async def verification_node(
        state: SentinelState,
    ) -> dict[str, object]:
        return await verification_agent.run(
            state
        )

    async def response_node(
        state: SentinelState,
    ) -> dict[str, object]:
        return await response_composer.run(
            state
        )

    builder = StateGraph(
        SentinelState
    )

    builder.add_node(
        "supervisor",
        supervisor_node,
    )

    builder.add_node(
        "procedure_agent",
        procedure_node,
    )

    builder.add_node(
        "incident_analyst",
        incident_node,
    )

    builder.add_node(
        "verification_agent",
        verification_node,
    )

    builder.add_node(
        "response_composer",
        response_node,
    )

    builder.add_edge(
        START,
        "supervisor",
    )

    builder.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "procedure_agent": "procedure_agent",
            "incident_analyst": "incident_analyst",
            "verification_agent": "verification_agent",
            "response_composer": "response_composer",
            "finish": END,
        },
    )

    builder.add_edge(
        "procedure_agent",
        "supervisor",
    )

    builder.add_edge(
        "incident_analyst",
        "supervisor",
    )

    builder.add_edge(
        "verification_agent",
        "supervisor",
    )

    builder.add_edge(
        "response_composer",
        END,
    )

    return builder.compile(
        checkpointer=checkpointer
    )