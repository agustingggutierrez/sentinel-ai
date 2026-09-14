from typing import Protocol

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.agents import IncidentAnalysis, VerificationResult
from app.models.retrieval import RetrievedChunk
from app.services.llm import OpenAIModelFactory


class StructuredVerificationModel(Protocol):
    """Minimal async interface required from the structured verifier LLM."""

    async def ainvoke(
        self,
        input: object,
    ) -> object:
        """Invoke the model asynchronously."""


class OpenAIVerifier:
    """Verify incident analysis against retrieved procedural evidence."""

    def __init__(
        self,
        factory: OpenAIModelFactory,
    ) -> None:
        self.model: StructuredVerificationModel = (
            factory.create_structured_model(
                VerificationResult
            )
        )

    async def verify(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
        analysis: IncidentAnalysis,
    ) -> VerificationResult:
        """Verify whether the analysis is supported by available evidence."""

        if not evidence:
            raise ValueError(
                "OpenAI Verifier requires evidence."
            )

        evidence_context = self._format_evidence(
            evidence
        )

        analysis_context = self._format_analysis(
            analysis
        )

        messages = [
            SystemMessage(
                content=(
                    "You are the Verification Agent for SentinelAI, "
                    "a physical security operations decision-support system. "
                    "Audit the incident analysis against the user report and "
                    "retrieved procedural evidence. Treat the analysis as a "
                    "claim to verify, not as ground truth. "
                    "Use status 'passed' only when the important claims are "
                    "supported. Use 'needs_more_evidence' when additional "
                    "specific information could resolve uncertainty. "
                    "Use 'failed' when material claims conflict with or are "
                    "unsupported by the available evidence and additional "
                    "retrieval is unlikely to resolve the problem. "
                    "List unsupported claims and missing information "
                    "explicitly. Do not invent facts. "
                    "Return the requested structured output only."
                )
            ),
            HumanMessage(
                content=(
                    "USER REPORT:\n"
                    f"{query}\n\n"
                    "INCIDENT ANALYSIS TO VERIFY:\n"
                    f"{analysis_context}\n\n"
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
            VerificationResult,
        ):
            raise TypeError(
                "Structured verification model did not return "
                "VerificationResult."
            )

        return result

    @staticmethod
    def _format_analysis(
        analysis: IncidentAnalysis,
    ) -> str:
        """Format structured incident analysis for verification."""

        risks = "\n".join(
            f"- {risk}"
            for risk in analysis.risks
        )

        return (
            f"severity: {analysis.severity}\n"
            f"summary: {analysis.summary}\n"
            f"risks:\n{risks}\n"
            "recommended_escalation: "
            f"{analysis.recommended_escalation}"
        )

    @staticmethod
    def _format_evidence(
        evidence: list[RetrievedChunk],
    ) -> str:
        """Format retrieved chunks for grounded verification."""

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