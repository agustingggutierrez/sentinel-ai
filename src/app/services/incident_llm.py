from typing import Protocol

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.agents import IncidentAnalysis
from app.models.retrieval import RetrievedChunk
from app.services.llm import OpenAIModelFactory


class StructuredIncidentModel(Protocol):
    """Minimal async interface required from the structured LLM."""

    async def ainvoke(
        self,
        input: object,
    ) -> object:
        """Invoke the model asynchronously."""


class OpenAIIncidentAnalyzer:
    """Analyze security incidents using grounded structured LLM output."""

    def __init__(
        self,
        factory: OpenAIModelFactory,
    ) -> None:
        self.model: StructuredIncidentModel = (
            factory.create_structured_model(
                IncidentAnalysis
            )
        )

    async def analyze(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
    ) -> IncidentAnalysis:
        """Analyze an incident using only the supplied RAG evidence."""

        if not evidence:
            raise ValueError(
                "OpenAI Incident Analyzer requires evidence."
            )

        evidence_context = self._format_evidence(
            evidence
        )

        messages = [
            SystemMessage(
                content=(
                    "You are the Incident Analyst for SentinelAI, "
                    "a physical security operations decision-support system. "
                    "Analyze the reported situation using only the supplied "
                    "procedural evidence. Do not invent identities, events, "
                    "authorizations, injuries, weapons, or actions that are "
                    "not supported by the user report or evidence. "
                    "Choose the severity conservatively. "
                    "Return the requested structured output only."
                )
            ),
            HumanMessage(
                content=(
                    "USER REPORT:\n"
                    f"{query}\n\n"
                    "RETRIEVED PROCEDURAL EVIDENCE:\n"
                    f"{evidence_context}"
                )
            ),
        ]

        result = await self.model.ainvoke(
            messages
        )

        if not isinstance(
            result,
            IncidentAnalysis,
        ):
            raise TypeError(
                "Structured incident model did not return IncidentAnalysis."
            )

        return result

    @staticmethod
    def _format_evidence(
        evidence: list[RetrievedChunk],
    ) -> str:
        """Format retrieved chunks for grounded LLM analysis."""

        sections: list[str] = []

        for index, chunk in enumerate(
            evidence,
            start=1,
        ):
            section = chunk.metadata.get(
                "section",
                "Unknown section",
            )

            sections.append(

                    f"[EVIDENCE {index}]\n"
                    f"document_id: {chunk.document_id}\n"
                    f"chunk_id: {chunk.chunk_id}\n"
                    f"section: {section}\n"
                    f"score: {chunk.score}\n"
                    f"content:\n{chunk.content}"

            )

        return "\n\n".join(
            sections
        )
