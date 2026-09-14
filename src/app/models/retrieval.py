from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RetrievedChunk(BaseModel):
    """Document chunk returned by the retrieval layer."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    document_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=256,
    )

    chunk_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
    )

    content: str = Field(
        ...,
        min_length=1,
    )

    score: float | None = Field(
        default=None,
        ge=0,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class RetrievalResult(BaseModel):
    """Validated result returned by the retrieval service."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        ...,
        min_length=3,
        max_length=4000,
    )

    chunks: list[RetrievedChunk] = Field(default_factory=list)

    total_found: int = Field(
        default=0,
        ge=0,
    )