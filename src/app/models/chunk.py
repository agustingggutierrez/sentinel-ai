from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunk(BaseModel):
    """Validated semantic chunk ready for embedding and indexing."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    chunk_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Deterministic identifier for the chunk.",
    )

    document_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=256,
    )

    category: str = Field(
        ...,
        min_length=1,
        max_length=128,
    )

    version: str = Field(
        ...,
        min_length=1,
        max_length=32,
    )

    priority: Literal[
        "low",
        "medium",
        "high",
        "critical",
    ]

    document_type: Literal[
        "policy",
        "procedure",
        "protocol",
        "matrix",
    ]

    section: str = Field(
        ...,
        min_length=1,
        max_length=256,
    )

    chunk_index: int = Field(
        ...,
        ge=0,
    )

    content: str = Field(
        ...,
        min_length=1,
    )

    source_path: str = Field(
        ...,
        min_length=1,
    )