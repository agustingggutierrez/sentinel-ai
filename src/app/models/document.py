from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentMetadata(BaseModel):
    """Validated metadata extracted from a SentinelAI knowledge document."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
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

    audience: str = Field(
        ...,
        min_length=1,
        max_length=128,
    )

    organization: str = Field(
        ...,
        min_length=1,
        max_length=256,
    )

    document_type: Literal[
        "policy",
        "procedure",
        "protocol",
        "matrix",
    ]


class ParsedDocument(BaseModel):
    """Validated document produced by the Markdown parsing layer."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    metadata: DocumentMetadata

    content: str = Field(
        ...,
        min_length=1,
        description="Markdown body without YAML front matter.",
    )

    source_path: str = Field(
        ...,
        min_length=1,
        description="Original path of the source document.",
    )