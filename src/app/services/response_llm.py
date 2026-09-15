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
                    "The final answer must be strictly grounded in the user "
                    "report and retrieved procedural evidence. "
                    "The incident analysis is supporting material, not an "
                    "independent source of truth. "
                    "Never introduce a factual claim solely because it "
                    "appears in the incident analysis. "
                    "Do not repeat any claim listed by the Verification "
                    "Agent as unsupported. "
                    "Do not infer that an event, threat, conflict, injury, "
                    "authorization, action, or condition did not occur merely "
                    "because it was not mentioned. Absence of information is "
                    "unknown, not evidence of absence. "
                    "Do not invent severity levels, escalation levels, "
                    "responsibilities, observations, camera evidence, "
                    "sanctions, investigations, or completed actions. "
                    "Only state a severity or escalation level when the "
                    "available evidence explicitly supports applying that "
                    "level to the reported facts. "
                    "Clearly distinguish reported facts from procedural "
                    "recommendations. "
                    "When evidence is insufficient for a factual conclusion, "
                    "say that it cannot be confirmed or omit the claim. "
                    "Prefer omission over unsupported inference. "
                    "Recommendations must be traceable to the retrieved "
                    "procedural evidence. "
                    "Prioritize immediate actions, escalation criteria, "
                    "record keeping, and relevant procedural guidance. "
                    "Do not claim that SentinelAI replaces human security "
                    "personnel, supervisors, emergency services, or local "
                    "procedures."
                )
            ),
            HumanMessage(
                content=(
                    "REPORTE DEL USUARIO:\n"
                    f"{query}\n\n"
                    "ANALISIS DEL INCIDENTE:\n"
                    f"Severidad: {analysis.severity}\n"
                    f"Resumen: {analysis.summary}\n"
                    f"Riesgos: {analysis.risks}\n"
                    "Escalamiento recomendado: "
                    f"{analysis.recommended_escalation}\n\n"
                    "RESULTADO DE VERIFICACION:\n"
                    f"Estado: {verification.status}\n"
                    f"Explicacion: {verification.explanation}\n"
                    "Afirmaciones no respaldadas: "
                    f"{verification.unsupported_claims}\n"
                    "Informacion faltante: "
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
                f"chunk_id: {chunk.chunk_id}\n"
                f"section: {section}\n"
                f"score: {chunk.score}\n"
                f"content:\n{chunk.content}"
            )

        return "\n\n".join(
            sections
        )