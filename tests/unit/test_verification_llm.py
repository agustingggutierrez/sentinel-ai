import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from app.models.agents import IncidentAnalysis, VerificationResult
from app.models.retrieval import RetrievedChunk
from app.services.verification_llm import OpenAIVerifier


def make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        document_id="restricted-areas",
        title="Restricted Areas",
        chunk_id="restricted-areas::002::authorization",
        content=(
            "Toda persona que ingrese a un área restringida "
            "debe contar con autorización específica vigente."
        ),
        score=0.95,
        metadata={
            "section": "Principio de autorización específica",
            "category": "restricted_areas",
        },
    )


def make_analysis() -> IncidentAnalysis:
    return IncidentAnalysis(
        severity="high",
        summary=(
            "Se reportó un posible acceso no autorizado."
        ),
        risks=[
            "Acceso a un sector restringido",
        ],
        recommended_escalation=(
            "Validar autorización y notificar a supervisión."
        ),
    )


def make_verification() -> VerificationResult:
    return VerificationResult(
        status="passed",
        explanation=(
            "La evidencia respalda los elementos principales "
            "del análisis."
        ),
        unsupported_claims=[],
        missing_information=[],
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
        self.schemas: list[type[VerificationResult]] = []

    def create_structured_model(
        self,
        schema: type[VerificationResult],
    ) -> FakeStructuredModel:
        self.schemas.append(schema)
        return self.model


def test_verifier_requests_verification_result_schema() -> None:
    model = FakeStructuredModel(
        make_verification()
    )

    factory = FakeFactory(
        model
    )

    OpenAIVerifier(
        factory
    )

    assert factory.schemas == [
        VerificationResult
    ]


@pytest.mark.asyncio
async def test_verifier_returns_structured_result() -> None:
    verifier = OpenAIVerifier(
        FakeFactory(
            FakeStructuredModel(
                make_verification()
            )
        )
    )

    result = await verifier.verify(
        query="un tecnico ingreso a un area restringida",
        evidence=[
            make_chunk()
        ],
        analysis=make_analysis(),
    )

    assert isinstance(
        result,
        VerificationResult,
    )

    assert result.status == "passed"


@pytest.mark.asyncio
async def test_verifier_sends_report_analysis_and_evidence() -> None:
    model = FakeStructuredModel(
        make_verification()
    )

    verifier = OpenAIVerifier(
        FakeFactory(
            model
        )
    )

    chunk = make_chunk()
    analysis = make_analysis()

    await verifier.verify(
        query="un tecnico ingreso sin autorizacion",
        evidence=[
            chunk
        ],
        analysis=analysis,
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

    assert analysis.summary in human_content
    assert analysis.severity in human_content
    assert chunk.document_id in human_content
    assert chunk.chunk_id in human_content
    assert chunk.content in human_content


@pytest.mark.asyncio
async def test_verifier_supports_needs_more_evidence() -> None:
    verification = VerificationResult(
        status="needs_more_evidence",
        explanation=(
            "No se puede confirmar la autorización."
        ),
        unsupported_claims=[
            "El técnico carece de autorización.",
        ],
        missing_information=[
            "Confirmar autorización vigente del técnico",
        ],
    )

    verifier = OpenAIVerifier(
        FakeFactory(
            FakeStructuredModel(
                verification
            )
        )
    )

    result = await verifier.verify(
        query="tecnico dentro de area restringida",
        evidence=[
            make_chunk()
        ],
        analysis=make_analysis(),
    )

    assert (
        result.status
        == "needs_more_evidence"
    )

    assert result.missing_information == [
        "Confirmar autorización vigente del técnico",
    ]


@pytest.mark.asyncio
async def test_verifier_requires_evidence() -> None:
    verifier = OpenAIVerifier(
        FakeFactory(
            FakeStructuredModel(
                make_verification()
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="requires evidence",
    ):
        await verifier.verify(
            query="consulta valida",
            evidence=[],
            analysis=make_analysis(),
        )


@pytest.mark.asyncio
async def test_verifier_rejects_unexpected_model_output() -> None:
    verifier = OpenAIVerifier(
        FakeFactory(
            FakeStructuredModel(
                {
                    "status": "passed",
                }
            )
        )
    )

    with pytest.raises(
        TypeError,
        match="did not return VerificationResult",
    ):
        await verifier.verify(
            query="consulta valida",
            evidence=[
                make_chunk()
            ],
            analysis=make_analysis(),
        )