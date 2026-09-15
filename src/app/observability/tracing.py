from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from langsmith import Client, traceable, tracing_context
from langsmith.run_helpers import get_current_run_tree

from app.config.settings import Settings


class ObservabilityConfigurationError(RuntimeError):
    """Raised when tracing is enabled without valid configuration."""


def _build_langsmith_client(
    settings: Settings,
) -> Client | None:
    """Create a LangSmith client only when cloud tracing is enabled."""

    if not settings.langsmith_tracing:
        return None

    api_key = settings.langsmith_api_key

    if api_key is None:
        raise ObservabilityConfigurationError(
            "LANGSMITH_API_KEY is required when "
            "LANGSMITH_TRACING is enabled."
        )

    secret = api_key.get_secret_value().strip()

    if not secret:
        raise ObservabilityConfigurationError(
            "LANGSMITH_API_KEY cannot be blank when "
            "LANGSMITH_TRACING is enabled."
        )

    return Client(
        api_key=secret,
    )


@contextmanager
def sentinel_tracing_context(
    *,
    settings: Settings,
    thread_id: str,
) -> Iterator[None]:
    """Configure tracing for one SentinelAI request."""

    client = _build_langsmith_client(
        settings
    )

    with tracing_context(
        project_name=settings.langsmith_project,
        tags=[
            "sentinel-ai",
            settings.app_env,
        ],
        metadata={
            "thread_id": thread_id,
            "llm_provider": settings.llm_provider,
        },
        enabled=settings.langsmith_tracing,
        client=client,
    ):
        yield


def _trace_inputs(
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Keep trace inputs useful while excluding runtime objects."""

    initial_state = inputs.get(
        "initial_state",
        {}
    )

    return {
        "query": initial_state.get(
            "query"
        ),
        "thread_id": initial_state.get(
            "thread_id"
        ),
    }


@traceable(
    name="sentinel_query",
    run_type="chain",
    process_inputs=_trace_inputs,
)
async def invoke_traced_graph(
    *,
    graph: Any,
    initial_state: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Execute LangGraph inside a traceable SentinelAI root span."""

    result = await graph.ainvoke(
        initial_state,
        config=config,
    )

    run_tree = get_current_run_tree()

    trace_id = (
        str(run_tree.trace_id)
        if run_tree is not None
        else None
    )

    if trace_id is not None:
        result["trace_id"] = trace_id

    return result
