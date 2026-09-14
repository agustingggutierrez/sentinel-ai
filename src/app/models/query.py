from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    """Request contract for a SentinelAI query."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(
        ...,
        min_length=3,
        max_length=4000,
        description="Security operations question or incident description.",
    )

    thread_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Conversation identifier used to preserve LangGraph state.",
    )