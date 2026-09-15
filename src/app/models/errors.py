from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ErrorCode = Literal[
    "runtime_unavailable",
    "workflow_failed",
    "workflow_incomplete",
    "internal_error",
]


class ErrorDetail(BaseModel):
    """Structured error information returned by the SentinelAI API."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    code: ErrorCode

    message: str = Field(
        ...,
        min_length=1,
        max_length=512,
    )

    thread_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
    )

    trace_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
    )


class ErrorResponse(BaseModel):
    """Stable error envelope returned by SentinelAI."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail