from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents.incident import IncidentAnalystService
from app.agents.procedure import ProcedureAgentService
from app.agents.response import ResponseComposerService
from app.agents.verification import VerificationAgentService
from app.config.settings import Settings, get_settings
from app.graph.workflow import build_sentinel_graph
from app.rag.retrieval import RetrievalService, create_retrieval_service
from app.services.incident_llm import LLMIncidentAnalyzer
from app.services.llm import LLMModelFactory
from app.services.response_llm import LLMResponseComposer
from app.services.supervisor_llm import LLMSupervisor
from app.services.verification_llm import LLMVerifier


@dataclass(slots=True)
class SentinelRuntime:
    """Application dependencies required to execute SentinelAI."""

    settings: Settings
    graph: Any
    retrieval_service: RetrievalService


@asynccontextmanager
async def create_sentinel_runtime(
    settings: Settings | None = None,
) -> AsyncIterator[SentinelRuntime]:
    """Create and safely dispose the complete SentinelAI runtime."""

    resolved_settings = settings or get_settings()

    checkpoint_path = resolved_settings.checkpoint_storage_path
    checkpoint_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    retrieval_service = create_retrieval_service(
        settings=resolved_settings,
    )

    llm_factory = LLMModelFactory(
        resolved_settings
    )

    procedure_agent = ProcedureAgentService(
        retrieval_service
    )

    incident_analyst = IncidentAnalystService(
        LLMIncidentAnalyzer(
            llm_factory
        )
    )

    verification_agent = VerificationAgentService(
        LLMVerifier(
            llm_factory
        )
    )

    response_composer = ResponseComposerService(
        LLMResponseComposer(
            llm_factory
        )
    )

    supervisor = LLMSupervisor(
        llm_factory
    )

    try:
        async with AsyncSqliteSaver.from_conn_string(
            str(checkpoint_path)
        ) as checkpointer:
            graph = build_sentinel_graph(
                procedure_agent=procedure_agent,
                incident_analyst=incident_analyst,
                verification_agent=verification_agent,
                response_composer=response_composer,
                supervisor=supervisor,
                checkpointer=checkpointer,
            )

            yield SentinelRuntime(
                settings=resolved_settings,
                graph=graph,
                retrieval_service=retrieval_service,
            )
    finally:
        await retrieval_service.client.close()
