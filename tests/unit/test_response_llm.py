import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.models.agents import IncidentAnalysis, VerificationResult
from app.models.retrieval import RetrievedChunk
from app.services.response_llm import OpenAIResponseComposer


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
        },
    )


def make_analysis() -> IncidentAnalysis:
    return IncidentAnalysis(
        severity="high",
        summary="Posible acceso no autorizado.",
        risks=[
            "Acceso a un área restringida",
        ],
        recommended_escalation=(
            "Validar autorización y notificar a supervisión."
        ),
    )


def make_verification() -> VerificationResult:
    return VerificationResult(
        status="passed",
        explanation="La evidencia respalda el análisis.",
        unsupported_claims=[],
        missing_information=[],
    )


class FakeChatModel:
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
        model: FakeChatModel,
    ) -> None:
        self.model = model
        self.create_calls = 0

    def create_chat_model(
        self,
    ) -> FakeChatModel:
        self.create_calls += 1
        return self.model


@pytest.mark.asyncio
async def test_composer_creates_chat_model() -> None:
    factory = FakeFactory(
        FakeChatModel(
            AIMessage(
                content="Respuesta."
            )
        )
    )

    OpenAIResponseComposer(
        factory
    )

    assert factory.create_calls == 1


@pytest.mark.asyncio
async def test_composer_returns_text_answer() -> None:
    composer = OpenAIResponseComposer(
        FakeFactory(
            FakeChatModel(
                AIMessage(
                    content="  Notifique a supervisión.  "
                )
            )
        )
    )

    result = await composer.compose(
        query="persona en area restringida",
        evidence=[
            make_chunk()
        ],
        analysis=make_analysis(),
        verification=make_verification(),
    )

    assert result == "Notifique a supervisión."


@pytest.mark.asyncio
async def test_composer_sends_complete_context() -> None:
    model = FakeChatModel(
        AIMessage(
            content="Respuesta final."
        )
    )

    composer = OpenAIResponseComposer(
        FakeFactory(
            model
        )
    )

    chunk = make_chunk()
    analysis = make_analysis()
    verification = make_verification()

    await composer.compose(
        query="un tecnico ingreso sin autorizacion",
        evidence=[
            chunk
        ],
        analysis=analysis,
        verification=verification,
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

    content = str(
        messages[1].content
    )

    assert (
        "un tecnico ingreso sin autorizacion"
        in content
    )

    assert analysis.summary in content
    assert verification.status in content
    assert chunk.document_id in content
    assert chunk.content in content


@pytest.mark.asyncio
async def test_composer_requires_evidence() -> None:
    composer = OpenAIResponseComposer(
        FakeFactory(
            FakeChatModel(
                AIMessage(
                    content="Respuesta."
                )
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="requires evidence",
    ):
        await composer.compose(
            query="consulta valida",
            evidence=[],
            analysis=make_analysis(),
            verification=make_verification(),
        )


@pytest.mark.asyncio
async def test_composer_rejects_unexpected_model_output() -> None:
    composer = OpenAIResponseComposer(
        FakeFactory(
            FakeChatModel(
                {
                    "answer": "Respuesta",
                }
            )
        )
    )

    with pytest.raises(
        TypeError,
        match="did not return AIMessage",
    ):
        await composer.compose(
            query="consulta valida",
            evidence=[
                make_chunk()
            ],
            analysis=make_analysis(),
            verification=make_verification(),
        )


@pytest.mark.asyncio
async def test_composer_rejects_empty_answer() -> None:
    composer = OpenAIResponseComposer(
        FakeFactory(
            FakeChatModel(
                AIMessage(
                    content="   "
                )
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="produced an empty answer",
    ):
        await composer.compose(
            query="consulta valida",
            evidence=[
                make_chunk()
            ],
            analysis=make_analysis(),
            verification=make_verification(),
        )