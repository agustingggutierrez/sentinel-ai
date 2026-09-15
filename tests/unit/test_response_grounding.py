import pytest
from langchain_core.messages import AIMessage, SystemMessage

from app.models.agents import IncidentAnalysis, VerificationResult
from app.models.retrieval import RetrievedChunk
from app.services.response_llm import OpenAIResponseComposer


class FakeChatModel:
    def __init__(self) -> None:
        self.inputs: list[object] = []

    async def ainvoke(
        self,
        input: object,
    ) -> object:
        self.inputs.append(input)

        return AIMessage(
            content="Respuesta fundamentada."
        )


class FakeFactory:
    def __init__(
        self,
        model: FakeChatModel,
    ) -> None:
        self.model = model

    def create_chat_model(
        self,
    ) -> FakeChatModel:
        return self.model


def make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        document_id="restricted-areas",
        title="Restricted Areas",
        chunk_id="restricted-areas::001::test",
        content=(
            "Toda persona que ingrese a un area restringida "
            "debe contar con autorizacion especifica vigente."
        ),
        score=0.95,
        metadata={
            "section": "Autorizacion especifica",
        },
    )


def make_analysis() -> IncidentAnalysis:
    return IncidentAnalysis(
        severity="medium",
        summary="Intento de acceso no autorizado.",
        risks=[
            "Acceso no autorizado.",
        ],
        recommended_escalation=(
            "Notificar a supervision."
        ),
    )


def make_verification() -> VerificationResult:
    return VerificationResult(
        status="passed",
        explanation="La evidencia respalda el hecho principal.",
        unsupported_claims=[
            "No se observo conflicto ni amenaza.",
        ],
        missing_information=[],
    )


@pytest.mark.asyncio
async def test_response_composer_enforces_grounding_rules() -> None:
    model = FakeChatModel()

    composer = OpenAIResponseComposer(
        FakeFactory(
            model
        )
    )

    await composer.compose(
        query=(
            "Un tecnico intento ingresar a un area restringida "
            "sin autorizacion."
        ),
        evidence=[
            make_chunk()
        ],
        analysis=make_analysis(),
        verification=make_verification(),
    )

    assert len(model.inputs) == 1

    messages = model.inputs[0]

    assert isinstance(
        messages,
        list,
    )

    system_message = messages[0]

    assert isinstance(
        system_message,
        SystemMessage,
    )

    content = str(
        system_message.content
    )

    assert (
        "not an independent source of truth"
        in content
    )

    assert (
        "Do not repeat any claim listed by the Verification Agent "
        "as unsupported"
        in content
    )

    assert (
        "Absence of information is unknown"
        in content
    )

    assert (
        "Do not invent severity levels"
        in content
    )

    assert (
        "Prefer omission over unsupported inference"
        in content
    )