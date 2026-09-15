from typing import Any

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from app.agents.incident import IncidentAnalystService
from app.agents.procedure import ProcedureAgentService
from app.agents.response import ResponseComposerService
from app.agents.supervisor import (
    SupervisorDecisionPort,
    supervisor_node,
)
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
    supervisor: SupervisorDecisionPort | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """Build and compile the SentinelAI multi-agent LangGraph."""

    async def supervisor_graph_node(
        state: SentinelState,
    ) -> dict[str, object]:
        if supervisor is None:
            return await supervisor_node(
                state
            )

        decision = await supervisor.decide(
            state
        )

        agents_used = [
            *state.get(
                "agents_used",
                [],
            ),
            "supervisor",
        ]

        return {
            "route": decision.next_node,
            "supervisor_reason": decision.reason,
            "agents_used": agents_used,
        }

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

    async def safe_response_node(
        state: SentinelState,
    ) -> dict[str, object]:
        verification = state.get(
            "verification_result"
        )

        if verification is None:
            raise RuntimeError(
                "Safe response requires a verification result."
            )

        explanation = verification.explanation.strip()

        unsupported_claims = [
            claim.strip()
            for claim in verification.unsupported_claims
            if claim.strip()
        ]

        missing_information = [
            item.strip()
            for item in verification.missing_information
            if item.strip()
        ]

        sections = [
            (
                "No hay evidencia suficiente para emitir una "
                "conclusion operativa plenamente verificada."
            ),
            f"Resultado de verificacion: {explanation}",
        ]

        if unsupported_claims:
            sections.append(
                "Afirmaciones que no deben asumirse como confirmadas:\n"
                + "\n".join(
                    f"- {claim}"
                    for claim in unsupported_claims
                )
            )

        if missing_information:
            sections.append(
                "Informacion adicional necesaria:\n"
                + "\n".join(
                    f"- {item}"
                    for item in missing_information
                )
            )

        sections.append(
            "La decision operativa final debe quedar en manos del "
            "personal responsable y de los procedimientos vigentes."
        )

        answer = "\n\n".join(
            sections
        )

        agents_used = [
            *state.get(
                "agents_used",
                [],
            ),
            "safe_response",
        ]

        return {
            "final_answer": answer,
            "messages": [
                AIMessage(
                    content=answer
                )
            ],
            "agents_used": agents_used,
        }

    builder = StateGraph(
        SentinelState
    )

    builder.add_node(
        "supervisor",
        supervisor_graph_node,
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

    builder.add_node(
        "safe_response",
        safe_response_node,
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
            "safe_response": "safe_response",
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

    builder.add_edge(
        "safe_response",
        END,
    )

    return builder.compile(
        checkpointer=checkpointer
    )