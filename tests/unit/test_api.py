from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.api.main as api_main
from app.config.settings import Settings
from app.models.response import SourceReference


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
            "final_answer": "Acceso rechazado y registrado.",
            "thread_id": state["thread_id"],
            "sources": [
                SourceReference(
                    document_id="access-control",
                    title="Control de acceso",
                    chunk_id="access-control::1",
                    score=0.91,
                )
            ],
            "retrieved_documents": [
                object(),
            ],
            "verification_result": SimpleNamespace(
                status="passed"
            ),
            "agents_used": [
                "supervisor",
                "procedure_agent",
                "incident_analyst",
                "verification_agent",
                "response_composer",
            ],
            "trace_id": "trace-test-001",
        }


def test_query_endpoint_returns_typed_response(
    monkeypatch,
) -> None:
    graph = FakeGraph()

    runtime = SimpleNamespace(
        graph=graph,
        settings=Settings(
            _env_file=None,
            graph_recursion_limit=40,
            langsmith_tracing=False,
        ),
    )

    @asynccontextmanager
    async def fake_runtime(
        settings=None,
    ):
        yield runtime

    monkeypatch.setattr(
        api_main,
        "create_sentinel_runtime",
        fake_runtime,
    )

    with TestClient(api_main.app) as client:
        response = client.post(
            "/v1/query",
            json={
                "query": (
                    "Un tecnico intento ingresar "
                    "a un area restringida."
                ),
                "thread_id": "api-test-thread",
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["answer"] == (
        "Acceso rechazado y registrado."
    )
    assert body["thread_id"] == "api-test-thread"
    assert body["metadata"]["verification_status"] == "passed"
    assert body["metadata"]["retrieval_count"] == 1
    assert body["trace_id"] == "trace-test-001"

    assert graph.config == {
        "configurable": {
            "thread_id": "api-test-thread",
        },
        "recursion_limit": 40,
    }


def test_query_endpoint_generates_thread_id(
    monkeypatch,
) -> None:
    graph = FakeGraph()

    runtime = SimpleNamespace(
        graph=graph,
        settings=Settings(
            _env_file=None,
            graph_recursion_limit=40,
            langsmith_tracing=False,
        ),
    )

    @asynccontextmanager
    async def fake_runtime(
        settings=None,
    ):
        yield runtime

    monkeypatch.setattr(
        api_main,
        "create_sentinel_runtime",
        fake_runtime,
    )

    with TestClient(api_main.app) as client:
        response = client.post(
            "/v1/query",
            json={
                "query": "Persona sin autorizacion en area restringida.",
            },
        )

    assert response.status_code == 200
    assert response.json()["thread_id"]
    assert graph.state["thread_id"]


def test_query_endpoint_rejects_short_query() -> None:
    with TestClient(api_main.app) as client:
        response = client.post(
            "/v1/query",
            json={
                "query": "a",
            },
        )

    assert response.status_code == 422
