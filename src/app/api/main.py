from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.errors import (
    RuntimeUnavailableError,
    SentinelAPIError,
    WorkflowExecutionError,
    WorkflowIncompleteError,
)
from app.bootstrap import SentinelRuntime, create_sentinel_runtime
from app.config.settings import get_settings
from app.graph.state import create_initial_state
from app.models.errors import ErrorDetail, ErrorResponse
from app.models.query import QueryRequest
from app.models.response import QueryMetadata, QueryResponse
from app.observability.logging import (
    configure_logging,
    get_logger,
)
from app.observability.tracing import (
    invoke_traced_graph,
    sentinel_tracing_context,
)

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage SentinelAI application startup and shutdown."""

    settings = get_settings()

    configure_logging(
        settings
    )

    logger.info(
        "Starting SentinelAI application.",
        extra={
            "event": "application_starting",
            "llm_provider": settings.llm_provider,
            "app_env": settings.app_env,
        },
    )

    try:
        async with create_sentinel_runtime(
            settings
        ) as runtime:
            app.state.runtime = runtime

            logger.info(
                "SentinelAI application ready.",
                extra={
                    "event": "application_ready",
                    "llm_provider": settings.llm_provider,
                    "app_env": settings.app_env,
                },
            )

            yield
    finally:
        logger.info(
            "Stopping SentinelAI application.",
            extra={
                "event": "application_stopping",
                "llm_provider": settings.llm_provider,
                "app_env": settings.app_env,
            },
        )


app = FastAPI(
    title="SentinelAI",
    description=(
        "Multi-Agent Security Operations Copilot "
        "built with RAG and LangGraph."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(SentinelAPIError)
async def sentinel_api_error_handler(
    _request: Request,
    exc: SentinelAPIError,
) -> JSONResponse:
    """Convert controlled SentinelAI failures into stable API responses."""

    logger.error(
        "SentinelAI API error.",
        extra={
            "event": "api_error",
            "thread_id": exc.thread_id,
            "trace_id": exc.trace_id,
            "error_code": exc.error_code,
        },
    )

    payload = ErrorResponse(
        error=ErrorDetail(
            code=exc.error_code,
            message=exc.public_message,
            thread_id=exc.thread_id,
            trace_id=exc.trace_id,
        )
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(
            mode="json"
        ),
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
        raise RuntimeUnavailableError()

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
    responses={
        500: {
            "model": ErrorResponse,
            "description": "Controlled SentinelAI workflow failure.",
        },
        503: {
            "model": ErrorResponse,
            "description": "SentinelAI runtime unavailable.",
        },
    },
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

    logger.info(
        "Processing SentinelAI query.",
        extra={
            "event": "query_started",
            "thread_id": thread_id,
            "llm_provider": runtime.settings.llm_provider,
            "app_env": runtime.settings.app_env,
        },
    )

    config = {
        "configurable": {
            "thread_id": thread_id,
        },
        "recursion_limit": (
            runtime.settings.graph_recursion_limit
        ),
    }

    started_at = perf_counter()

    try:
        with sentinel_tracing_context(
            settings=runtime.settings,
            thread_id=thread_id,
        ):
            result = await invoke_traced_graph(
                graph=runtime.graph,
                initial_state=initial_state,
                config=config,
            )
    except SentinelAPIError:
        raise
    except Exception as exc:
        logger.exception(
            "SentinelAI workflow execution failed.",
            extra={
                "event": "workflow_failed",
                "thread_id": thread_id,
                "error_code": "workflow_failed",
            },
        )

        raise WorkflowExecutionError(
            thread_id=thread_id,
        ) from exc

    duration_ms = (
        perf_counter() - started_at
    ) * 1000

    final_answer = result.get(
        "final_answer"
    )

    if not final_answer:
        raise WorkflowIncompleteError(
            thread_id=thread_id,
            trace_id=result.get(
                "trace_id"
            ),
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

    trace_id = result.get(
        "trace_id"
    )

    logger.info(
        "SentinelAI query completed.",
        extra={
            "event": "query_completed",
            "thread_id": result.get(
                "thread_id",
                thread_id,
            ),
            "trace_id": trace_id,
            "duration_ms": duration_ms,
            "llm_provider": runtime.settings.llm_provider,
            "app_env": runtime.settings.app_env,
        },
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
        trace_id=trace_id,
    )