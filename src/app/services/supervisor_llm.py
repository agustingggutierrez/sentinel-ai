from typing import Protocol

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.state import SentinelState
from app.models.agents import SupervisorDecision
from app.services.llm import LLMModelFactory


class StructuredSupervisorModel(Protocol):
    """Minimal async interface required from the structured supervisor LLM."""

    async def ainvoke(
        self,
        input: object,
    ) -> object:
        """Invoke the model asynchronously."""


class LLMSupervisor:
    """Choose the next SentinelAI graph node from the current shared state."""

    def __init__(
        self,
        factory: LLMModelFactory,
    ) -> None:
        self.model: StructuredSupervisorModel = (
            factory.create_structured_model(
                SupervisorDecision
            )
        )

    async def decide(
        self,
        state: SentinelState,
    ) -> SupervisorDecision:
        """Choose the next graph route using the complete current state."""

        state_context = self._format_state(
            state
        )

        messages = [
            SystemMessage(
                content=(
                    "You are the Supervisor for SentinelAI, "
                    "a multi-agent physical security operations "
                    "decision-support system. "
                    "Choose exactly one next graph node based on the "
                    "current shared state. "
                    "Do not follow a fixed sequence blindly. "
                    "Delegate according to what work is actually missing. "
                    "Use procedure_agent when procedural evidence is missing "
                    "or when verification explicitly requests more evidence "
                    "and the retry limit has not been reached. "
                    "Use incident_analyst when evidence is available but a "
                    "current structured incident analysis is missing. "
                    "Use verification_agent when evidence and incident "
                    "analysis are available but the analysis still requires "
                    "verification. "
                    "Use response_composer only when verification status is "
                    "'passed' and sufficient verified material exists. "
                    "Use safe_response when verification status is 'failed'. "
                    "Also use safe_response when verification still requires "
                    "more evidence but the retry limit has been reached. "
                    "Use finish only when a final answer already exists. "
                    "Never invent state that is not present. "
                    "Return the requested structured output only."
                )
            ),
            HumanMessage(
                content=(
                    "CURRENT SENTINELAI STATE:\n"
                    f"{state_context}"
                )
            ),
        ]

        result = await self.model.ainvoke(
            messages
        )

        if not isinstance(
            result,
            SupervisorDecision,
        ):
            raise TypeError(
                "Structured supervisor model did not return "
                "SupervisorDecision."
            )

        return result

    @staticmethod
    def _format_state(
        state: SentinelState,
    ) -> str:
        """Format only routing-relevant state for the supervisor."""

        retrieved_documents = state.get(
            "retrieved_documents",
            [],
        )

        document_ids = [
            chunk.document_id
            for chunk in retrieved_documents
        ]

        analysis = state.get(
            "incident_analysis"
        )

        verification = state.get(
            "verification_result"
        )

        final_answer = state.get(
            "final_answer"
        )

        analysis_status = (
            "present"
            if analysis is not None
            else "missing"
        )

        verification_status = (
            verification.status
            if verification is not None
            else "not_run"
        )

        final_answer_status = (
            "present"
            if final_answer
            else "missing"
        )

        return (
            f"query: {state.get('query', '')}\n"
            f"retrieved_document_count: {len(retrieved_documents)}\n"
            f"retrieved_document_ids: {document_ids}\n"
            f"incident_analysis: {analysis_status}\n"
            f"verification_status: {verification_status}\n"
            f"retry_count: {state.get('retry_count', 0)}\n"
            f"final_answer: {final_answer_status}"
        )


OpenAISupervisor = LLMSupervisor
