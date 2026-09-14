from typing import Protocol

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.models.agents import IncidentAnalysis, VerificationResult
from app.models.retrieval import RetrievedChunk
from app.services.llm import OpenAIModelFactory


class ChatResponseModel(Protocol):
    """Minimal async interface required from the response LLM."""

    async def ainvoke(
        self,
        input: object,
    ) -> object:
        """Invoke the model asynchronously."""


class OpenAIResponseComposer:
    """Compose a grounded user-facing security operations response."""

    def __init__(
        self,
        factory: OpenAIModelFactory,
    ) -> None:
        self.model: ChatResponseModel = (
            factory.create_chat_model()
        )

    async def compose(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
        analysis: IncidentAnalysis,
        verification: VerificationResult,
    ) -> str:
        """Compose the final answer from verified graph state."""

        if not evidence:
            raise ValueError(
                "OpenAI Response Composer requires evidence."
            )

        evidence_context = self._format_evidence(
            evidence
        )

        messages = [
            SystemMessage(
                content=(
                    "You are the Response Composer for SentinelAI, "
                    "a physical security operations decision-support system. "
                    "Write a concise, operational response in Spanish. "
                    "Base the answer only on the user report, retrieved "
                    "procedures, incident analysis, and verification result. "
                    "Do not invent facts. "
                    "Clearly distinguish confirmed information from "
                    "uncertainty. "
                    "Prioritize immediate actions, escalation, and relevant "
                    "procedural guidance. "
                    "Do not claim that SentinelAI replaces human security "
                    "personnel, supervisors, emergency services, or local "
                    "procedures."
                )
            ),
            HumanMessage(
                content=(
                    "REPORTE DEL USUARIO:\n"
                    f"{query}\n\n"
                    "ANÁLISIS DEL INCIDENTE:\n"
                    f"Severidad: {analysis.severity}\n"
                    f"Resumen: {analysis.summary}\n"
                    f"Riesgos: {analysis.risks}\n"
                    "Escalamiento recomendado: "
                    f"{analysis.recommended_escalation}\n\n"
                    "RESULTADO DE VERIFICACIÓN:\n"
                    f"Estado: {verification.status}\n"
                    f"Explicación: {verification.explanation}\n"
                    "Afirmaciones no respaldadas: "
                    f"{verification.unsupported_claims}\n"
                    "Información faltante: "
                    f"{verification.missing_information}\n\n"
                    "EVIDENCIA PROCEDIMENTAL:\n"
                    f"{evidence_context}"
                )
            ),
        ]

        result = await self.model.ainvoke(
            messages
        )

        if not isinstance(
            result,
            AIMessage,
        ):
            raise TypeError(
                "Response model did not return AIMessage."
            )

        if not isinstance(
            result.content,
            str,
        ):
            raise TypeError(
                "Response model returned non-text content."
            )

        answer = result.content.strip()

        if not answer:
            raise ValueError(
                "Response model produced an empty answer."
            )

        return answer

    @staticmethod
    def _format_evidence(
        evidence: list[RetrievedChunk],
    ) -> str:
        """Format retrieved evidence for final response composition."""

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
                f"section: {section}\n"
                f"content:\n{chunk.content}"
            )

        return "\n\n".join(
            sections
        )