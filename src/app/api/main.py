from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request

from app.bootstrap import SentinelRuntime, create_sentinel_runtime
from app.config.settings import get_settings
from app.graph.state import create_initial_state
from app.models.query import QueryRequest
from app.models.response import QueryMetadata, QueryResponse
from app.observability.tracing import (
    invoke_traced_graph,
    sentinel_tracing_context,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage SentinelAI application startup and shutdown."""

    settings = get_settings()

    async with create_sentinel_runtime(
        settings
    ) as runtime:
        app.state.runtime = runtime
        yield


app = FastAPI(
    title="SentinelAI",
    description=(
        "Multi-Agent Security Operations Copilot "
        "built with RAG and LangGraph."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


def get_runtime(
    request: Request,
) -> SentinelRuntime:
    """Return the active SentinelAI runtime."""

    runtime = getattr(
        request.app.state,
        "runtime",
        None,
    )

    if runtime is None:
        raise RuntimeError(
            "SentinelAI runtime is not initialized."
        )

    return runtime


@app.get(
    "/health",
    tags=["health"],
)
async def health() -> dict[str, str]:
    """Return a lightweight application health response."""

    return {
        "status": "ok",
        "service": "SentinelAI",
    }


@app.post(
    "/v1/query",
    response_model=QueryResponse,
    tags=["queries"],
)
async def query_sentinel(
    payload: QueryRequest,
    request: Request,
) -> QueryResponse:
    """Execute the SentinelAI multi-agent workflow."""

    runtime = get_runtime(
        request
    )

    initial_state = create_initial_state(
        payload.query,
        thread_id=payload.thread_id,
    )

    thread_id = initial_state["thread_id"]

    config = {
        "configurable": {
            "thread_id": thread_id,
        },
        "recursion_limit": (
            runtime.settings.graph_recursion_limit
        ),
    }

    started_at = perf_counter()

    with sentinel_tracing_context(
        settings=runtime.settings,
        thread_id=thread_id,
    ):
        result = await invoke_traced_graph(
            graph=runtime.graph,
            initial_state=initial_state,
            config=config,
        )

    duration_ms = (
        perf_counter() - started_at
    ) * 1000

    final_answer = result.get(
        "final_answer"
    )

    if not final_answer:
        raise RuntimeError(
            "SentinelAI graph completed without a final answer."
        )

    verification = result.get(
        "verification_result"
    )

    verification_status = (
        verification.status
        if verification is not None
        else "not_run"
    )

    retrieved_documents = result.get(
        "retrieved_documents",
        [],
    )

    return QueryResponse(
        answer=final_answer,
        thread_id=result.get(
            "thread_id",
            thread_id,
        ),
        sources=result.get(
            "sources",
            [],
        ),
        metadata=QueryMetadata(
            agents_used=result.get(
                "agents_used",
                [],
            ),
            retrieval_count=len(
                retrieved_documents
            ),
            verification_status=verification_status,
            duration_ms=duration_ms,
        ),
        trace_id=result.get(
            "trace_id"
        ),
    )
