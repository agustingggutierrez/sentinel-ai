import pytest

from app.config.settings import Settings
from app.observability.tracing import (
    ObservabilityConfigurationError,
    invoke_traced_graph,
    sentinel_tracing_context,
)


class FakeGraph:
    def __init__(self) -> None:
        self.state = None
        self.config = None

    async def ainvoke(
        self,
        state,
        config,
    ):
        self.state = state
        self.config = config

        return {
            "final_answer": "Respuesta verificada.",
            "thread_id": state["thread_id"],
        }


def test_tracing_disabled_does_not_require_api_key() -> None:
    settings = Settings(
        _env_file=None,
        langsmith_tracing=False,
        langsmith_api_key=None,
    )

    with sentinel_tracing_context(
        settings=settings,
        thread_id="trace-disabled",
    ):
        pass


def test_tracing_enabled_requires_api_key() -> None:
    settings = Settings(
        _env_file=None,
        langsmith_tracing=True,
        langsmith_api_key=None,
    )

    with pytest.raises(
        ObservabilityConfigurationError,
        match="LANGSMITH_API_KEY is required",
    ), sentinel_tracing_context(
        settings=settings,
        thread_id="trace-missing-key",
    ):
        pass


@pytest.mark.asyncio
async def test_traced_graph_executes_when_tracing_is_disabled() -> None:
    settings = Settings(
        _env_file=None,
        langsmith_tracing=False,
    )

    graph = FakeGraph()

    state = {
        "query": "Persona en area restringida.",
        "thread_id": "trace-graph-test",
    }

    config = {
        "configurable": {
            "thread_id": "trace-graph-test",
        },
        "recursion_limit": 40,
    }

    with sentinel_tracing_context(
        settings=settings,
        thread_id="trace-graph-test",
    ):
        result = await invoke_traced_graph(
            graph=graph,
            initial_state=state,
            config=config,
        )

    assert result["final_answer"] == "Respuesta verificada."
    assert result["thread_id"] == "trace-graph-test"
    assert graph.state == state
    assert graph.config == config

@pytest.mark.asyncio
async def test_traced_graph_adds_trace_id(
    monkeypatch,
) -> None:
    graph = FakeGraph()

    class FakeRunTree:
        trace_id = "trace-unit-123"

    monkeypatch.setattr(
        "app.observability.tracing.get_current_run_tree",
        lambda: FakeRunTree(),
    )

    result = await invoke_traced_graph(
        graph=graph,
        initial_state={
            "query": "Consulta operativa.",
            "thread_id": "trace-id-test",
        },
        config={
            "configurable": {
                "thread_id": "trace-id-test",
            },
            "recursion_limit": 40,
        },
    )

    assert result["trace_id"] == "trace-unit-123"
