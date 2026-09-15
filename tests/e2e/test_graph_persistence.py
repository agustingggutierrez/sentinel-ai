from pathlib import Path

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents.incident import IncidentAnalystService
from app.agents.procedure import ProcedureAgentService
from app.agents.response import ResponseComposerService
from app.agents.verification import VerificationAgentService
from app.graph.state import create_initial_state
from app.graph.workflow import build_sentinel_graph
from app.models.agents import IncidentAnalysis, VerificationResult
from app.models.retrieval import RetrievalResult, RetrievedChunk


def make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        document_id="restricted-areas",
        title="Restricted Areas",
        chunk_id="restricted-areas::001::persistence",
        content=(
            "Toda persona en un área restringida "
            "debe contar con autorización específica."
        ),
        score=0.97,
        metadata={
            "category": "restricted_areas",
            "section": "Autorización específica",
        },
    )


class FakeRetrieval:
    async def retrieve(
        self,
        query: str,
        *,
        category: str | None = None,
        priority: str | None = None,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> RetrievalResult:
        return RetrievalResult(
            query=query,
            chunks=[make_chunk()],
            total_found=1,
        )


class FakeAnalyzer:
    async def analyze(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
    ) -> IncidentAnalysis:
        return IncidentAnalysis(
            severity="high",
            summary="Posible acceso no autorizado.",
            risks=[
                "Acceso no autorizado",
            ],
            recommended_escalation=(
                "Verificar autorización y notificar a supervisión."
            ),
        )


class FakeVerifier:
    async def verify(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
        analysis: IncidentAnalysis,
    ) -> VerificationResult:
        return VerificationResult(
            status="passed",
            explanation=(
                "La evidencia disponible respalda el análisis."
            ),
            unsupported_claims=[],
            missing_information=[],
        )


class FakeComposer:
    async def compose(
        self,
        *,
        query: str,
        evidence: list[RetrievedChunk],
        analysis: IncidentAnalysis,
        verification: VerificationResult,
    ) -> str:
        return (
            "Verifique la autorización de la persona "
            "y notifique a supervisión."
        )


def build_graph(
    checkpointer: AsyncSqliteSaver,
):
    return build_sentinel_graph(
        procedure_agent=ProcedureAgentService(
            FakeRetrieval()
        ),
        incident_analyst=IncidentAnalystService(
            FakeAnalyzer()
        ),
        verification_agent=VerificationAgentService(
            FakeVerifier()
        ),
        response_composer=ResponseComposerService(
            FakeComposer()
        ),
        checkpointer=checkpointer,
    )


@pytest.mark.asyncio
async def test_graph_state_persists_across_checkpointer_connections(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "checkpoints.sqlite"
    )

    config = {
        "configurable": {
            "thread_id": "persistence-thread",
        }
    }

    initial_state = create_initial_state(
        "persona sin autorizacion en area restringida",
        thread_id="persistence-thread",
    )

    async with AsyncSqliteSaver.from_conn_string(
        str(database_path)
    ) as first_checkpointer:
        graph = build_graph(
            first_checkpointer
        )

        result = await graph.ainvoke(
            initial_state,
            config=config,
        )

        assert result["final_answer"] == (
            "Verifique la autorización de la persona "
            "y notifique a supervisión."
        )

        first_snapshot = await graph.aget_state(
            config
        )

        assert first_snapshot.values["thread_id"] == (
            "persistence-thread"
        )

        assert first_snapshot.values["final_answer"]

    assert database_path.exists()

    async with AsyncSqliteSaver.from_conn_string(
        str(database_path)
    ) as second_checkpointer:
        restored_graph = build_graph(
            second_checkpointer
        )

        restored_snapshot = (
            await restored_graph.aget_state(
                config
            )
        )

        assert (
            restored_snapshot.values["thread_id"]
            == "persistence-thread"
        )

        assert restored_snapshot.values["final_answer"] == (
            "Verifique la autorización de la persona "
            "y notifique a supervisión."
        )

        assert (
            restored_snapshot.values[
                "verification_result"
            ].status
            == "passed"
        )

        assert len(
            restored_snapshot.values[
                "retrieved_documents"
            ]
        ) == 1