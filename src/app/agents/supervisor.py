from app.graph.state import SentinelState
from app.models.agents import SupervisorDecision


class SupervisorService:
    """Temporary deterministic supervisor policy for graph development."""

    def decide(
        self,
        state: SentinelState,
    ) -> SupervisorDecision:
        """Choose the next graph node from the current shared state."""

        verification = state.get(
            "verification_result"
        )

        retry_count = state.get(
            "retry_count",
            0,
        )

        if verification is not None:
            if (
                verification.status
                == "needs_more_evidence"
                and retry_count < 2
            ):
                return SupervisorDecision(
                    next_node="procedure_agent",
                    reason=(
                        "Verification requested additional evidence."
                    ),
                )

            if verification.status == "passed":
                return SupervisorDecision(
                    next_node="response_composer",
                    reason=(
                        "Verification passed and the response "
                        "can be composed."
                    ),
                )

            if verification.status == "failed":
                return SupervisorDecision(
                    next_node="response_composer",
                    reason=(
                        "Verification failed; compose a cautious "
                        "response with the available evidence."
                    ),
                )

            if retry_count >= 2:
                return SupervisorDecision(
                    next_node="response_composer",
                    reason=(
                        "Maximum evidence retries reached."
                    ),
                )

        retrieved_documents = state.get(
            "retrieved_documents",
            [],
        )

        if not retrieved_documents:
            return SupervisorDecision(
                next_node="procedure_agent",
                reason=(
                    "No supporting procedure evidence "
                    "has been retrieved yet."
                ),
            )

        if state.get("incident_analysis") is None:
            return SupervisorDecision(
                next_node="incident_analyst",
                reason=(
                    "Evidence is available but incident analysis "
                    "has not been performed."
                ),
            )

        return SupervisorDecision(
            next_node="verification_agent",
            reason=(
                "Incident analysis and evidence are available "
                "and must be verified."
            ),
        )


async def supervisor_node(
    state: SentinelState,
) -> dict[str, object]:
    """LangGraph node that stores the supervisor routing decision."""

    decision = SupervisorService().decide(
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