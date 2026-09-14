import pytest
from pydantic import BaseModel, SecretStr

import app.services.llm as llm_module
from app.config.settings import Settings
from app.services.llm import (
    LLMConfigurationError,
    LLMModelFactory,
)


class ExampleStructuredOutput(BaseModel):
    result: str


class FakeChatGroq:
    last_kwargs: dict[str, object] | None = None

    def __init__(
        self,
        **kwargs: object,
    ) -> None:
        FakeChatGroq.last_kwargs = kwargs

    def with_structured_output(
        self,
        schema: type[BaseModel],
        *,
        method: str,
        strict: bool,
    ) -> dict[str, object]:
        return {
            "schema": schema,
            "method": method,
            "strict": strict,
        }


def test_groq_factory_rejects_missing_api_key() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="groq",
        groq_api_key=None,
    )

    factory = LLMModelFactory(
        settings
    )

    with pytest.raises(
        LLMConfigurationError,
        match="GROQ_API_KEY is required",
    ):
        factory.create_chat_model()


def test_groq_factory_rejects_blank_api_key() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="groq",
        groq_api_key=SecretStr("   "),
    )

    factory = LLMModelFactory(
        settings
    )

    with pytest.raises(
        LLMConfigurationError,
        match="cannot be blank",
    ):
        factory.create_chat_model()


def test_groq_factory_uses_configured_model_and_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        llm_module,
        "ChatGroq",
        FakeChatGroq,
    )

    settings = Settings(
        _env_file=None,
        llm_provider="groq",
        groq_api_key=SecretStr(
            "gsk-test-secret"
        ),
        groq_model="openai/gpt-oss-20b",
    )

    factory = LLMModelFactory(
        settings
    )

    factory.create_chat_model()

    assert FakeChatGroq.last_kwargs is not None

    assert (
        FakeChatGroq.last_kwargs["model"]
        == "openai/gpt-oss-20b"
    )

    assert (
        FakeChatGroq.last_kwargs["api_key"]
        == "gsk-test-secret"
    )

    assert (
        FakeChatGroq.last_kwargs["temperature"]
        == 0
    )


def test_groq_factory_creates_strict_structured_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        llm_module,
        "ChatGroq",
        FakeChatGroq,
    )

    settings = Settings(
        _env_file=None,
        llm_provider="groq",
        groq_api_key=SecretStr(
            "gsk-test-secret"
        ),
    )

    factory = LLMModelFactory(
        settings
    )

    structured_model = (
        factory.create_structured_model(
            ExampleStructuredOutput
        )
    )

    assert structured_model == {
        "schema": ExampleStructuredOutput,
        "method": "json_schema",
        "strict": True,
    }