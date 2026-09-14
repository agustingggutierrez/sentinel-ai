import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from app.models.agents import IncidentAnalysis
from app.models.retrieval import RetrievedChunk
from app.services.incident_llm import OpenAIIncidentAnalyzer


def make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        document_id="restricted-areas",
        title="Restricted Areas",
        chunk_id="restricted-areas::002::authorization",
        content=(
            "Toda persona que ingrese a un área restringida "
            "debe contar con autorización específica vigente."
        ),
        score=0.94,
        metadata={
            "section": "Principio de autorización específica",
            "category": "restricted_areas",
        },
    )


class FakeStructuredModel:
    def __init__(
        self,
        result: object,
    ) -> None:
        self.result = result
        self.inputs: list[object] = []

    async def ainvoke(
        self,
        input: object,
    ) -> object:
        self.inputs.append(input)
        return self.result


class FakeFactory:
    def __init__(
        self,
        model: FakeStructuredModel,
    ) -> None:
        self.model = model
        self.schemas: list[type[IncidentAnalysis]] = []

    def create_structured_model(
        self,
        schema: type[IncidentAnalysis],
    ) -> FakeStructuredModel:
        self.schemas.append(schema)
        return self.model


def make_analysis() -> IncidentAnalysis:
    return IncidentAnalysis(
        severity="high",
        summary="Posible acceso no autorizado.",
        risks=[
            "Acceso a un sector restringido",
        ],
        recommended_escalation=(
            "Validar autorización y notificar a supervisión."
        ),
    )


@pytest.mark.asyncio
async def test_analyzer_requests_incident_analysis_schema() -> None:
    model = FakeStructuredModel(
        make_analysis()
    )

    factory = FakeFactory(
        model
    )

    OpenAIIncidentAnalyzer(
        factory
    )

    assert factory.schemas == [
        IncidentAnalysis
    ]


@pytest.mark.asyncio
async def test_analyzer_returns_structured_incident_analysis() -> None:
    analyzer = OpenAIIncidentAnalyzer(
        FakeFactory(
            FakeStructuredModel(
                make_analysis()
            )
        )
    )

    result = await analyzer.analyze(
        query="un tecnico ingreso a un area restringida",
        evidence=[
            make_chunk()
        ],
    )

    assert isinstance(
        result,
        IncidentAnalysis,
    )

    assert result.severity == "high"


@pytest.mark.asyncio
async def test_analyzer_sends_query_and_evidence_to_model() -> None:
    model = FakeStructuredModel(
        make_analysis()
    )

    analyzer = OpenAIIncidentAnalyzer(
        FakeFactory(
            model
        )
    )

    chunk = make_chunk()

    await analyzer.analyze(
        query="un tecnico ingreso sin autorizacion",
        evidence=[
            chunk
        ],
    )

    assert len(model.inputs) == 1

    messages = model.inputs[0]

    assert isinstance(
        messages,
        list,
    )

    assert isinstance(
        messages[0],
        SystemMessage,
    )

    assert isinstance(
        messages[1],
        HumanMessage,
    )

    human_content = str(
        messages[1].content
    )

    assert (
        "un tecnico ingreso sin autorizacion"
        in human_content
    )

    assert chunk.document_id in human_content
    assert chunk.chunk_id in human_content
    assert chunk.content in human_content


@pytest.mark.asyncio
async def test_analyzer_requires_evidence() -> None:
    analyzer = OpenAIIncidentAnalyzer(
        FakeFactory(
            FakeStructuredModel(
                make_analysis()
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="requires evidence",
    ):
        await analyzer.analyze(
            query="consulta valida",
            evidence=[],
        )


@pytest.mark.asyncio
async def test_analyzer_rejects_unexpected_model_output() -> None:
    analyzer = OpenAIIncidentAnalyzer(
        FakeFactory(
            FakeStructuredModel(
                {
                    "severity": "high",
                }
            )
        )
    )

    with pytest.raises(
        TypeError,
        match="did not return IncidentAnalysis",
    ):
        await analyzer.analyze(
            query="consulta valida",
            evidence=[
                make_chunk()
            ],
        )