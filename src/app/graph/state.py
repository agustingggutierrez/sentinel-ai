from typing import Annotated, TypedDict
from uuid import uuid4

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages

from app.models.agents import (
    AgentRoute,
    IncidentAnalysis,
    VerificationResult,
)
from app.models.response import SourceReference
from app.models.retrieval import RetrievedChunk


class SentinelState(TypedDict, total=False):
    """Shared state passed between all SentinelAI LangGraph nodes."""

    messages: Annotated[
        list[BaseMessage],
        add_messages,
    ]

    query: str
    thread_id: str

    route: AgentRoute | None
    supervisor_reason: str | None

    retrieved_documents: list[RetrievedChunk]
    sources: list[SourceReference]

    incident_analysis: IncidentAnalysis | None
    verification_result: VerificationResult | None

    retry_count: int
    agents_used: list[str]

    final_answer: str | None
    trace_id: str | None


def create_initial_state(
    query: str,
    *,
    thread_id: str | None = None,
) -> SentinelState:
    """Create a validated initial graph state for a user query."""

    normalized_query = query.strip()

    if len(normalized_query) < 3:
        raise ValueError(
            "Graph query must contain at least 3 characters."
        )

    if thread_id is not None:
        normalized_thread_id = thread_id.strip()

        if not normalized_thread_id:
            raise ValueError(
                "thread_id cannot be blank."
            )
    else:
        normalized_thread_id = str(uuid4())

    return SentinelState(
        messages=[
            HumanMessage(
                content=normalized_query,
            )
        ],
        query=normalized_query,
        thread_id=normalized_thread_id,
        route=None,
        supervisor_reason=None,
        retrieved_documents=[],
        sources=[],
        incident_analysis=None,
        verification_result=None,
        retry_count=0,
        agents_used=[],
        final_answer=None,
        trace_id=None,
    )