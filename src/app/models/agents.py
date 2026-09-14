from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AgentRoute = Literal[
    "procedure_agent",
    "incident_analyst",
    "verification_agent",
    "response_composer",
    "finish",
]


class SupervisorDecision(BaseModel):
    """Structured routing decision produced by the supervisor."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    next_node: AgentRoute = Field(
        ...,
        description="Next LangGraph node selected by the supervisor.",
    )

    reason: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Short explanation for the routing decision.",
    )


class IncidentAnalysis(BaseModel):
    """Structured security incident assessment."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    severity: Literal[
        "low",
        "medium",
        "high",
        "critical",
    ]

    summary: str = Field(
        ...,
        min_length=3,
        max_length=2000,
    )

    risks: list[str] = Field(default_factory=list)

    recommended_escalation: str | None = Field(
        default=None,
        max_length=1000,
    )


class VerificationResult(BaseModel):
    """Result of checking an answer against retrieved evidence."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    status: Literal[
        "passed",
        "needs_more_evidence",
        "failed",
    ]

    explanation: str = Field(
        ...,
        min_length=3,
        max_length=2000,
    )

    unsupported_claims: list[str] = Field(default_factory=list)

    missing_information: list[str] = Field(default_factory=list)