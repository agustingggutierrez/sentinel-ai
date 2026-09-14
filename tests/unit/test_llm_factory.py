import pytest
from pydantic import BaseModel, SecretStr

import app.services.llm as llm_module
from app.config.settings import Settings
from app.services.llm import (
    OpenAIConfigurationError,
    OpenAIModelFactory,
)


class ExampleStructuredOutput(BaseModel):
    result: str


class FakeChatOpenAI:
    last_kwargs: dict[str, object] | None = None

    def __init__(
        self,
        **kwargs: object,
    ) -> None:
        FakeChatOpenAI.last_kwargs = kwargs

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


def test_factory_rejects_missing_api_key() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key=None,
    )

    factory = OpenAIModelFactory(
        settings
    )

    with pytest.raises(
        OpenAIConfigurationError,
        match="OPENAI_API_KEY is required",
    ):
        factory.create_chat_model()


def test_factory_rejects_blank_api_key() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key=SecretStr("   "),
    )

    factory = OpenAIModelFactory(
        settings
    )

    with pytest.raises(
        OpenAIConfigurationError,
        match="cannot be blank",
    ):
        factory.create_chat_model()


def test_factory_uses_configured_model_and_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        llm_module,
        "ChatOpenAI",
        FakeChatOpenAI,
    )

    settings = Settings(
        _env_file=None,
        openai_api_key=SecretStr(
            "sk-test-secret"
        ),
        openai_model="gpt-5.6-luna",
    )

    factory = OpenAIModelFactory(
        settings
    )

    factory.create_chat_model()

    assert FakeChatOpenAI.last_kwargs is not None

    assert (
        FakeChatOpenAI.last_kwargs["model"]
        == "gpt-5.6-luna"
    )

    assert (
        FakeChatOpenAI.last_kwargs["api_key"]
        == "sk-test-secret"
    )


def test_factory_creates_strict_structured_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        llm_module,
        "ChatOpenAI",
        FakeChatOpenAI,
    )

    settings = Settings(
        _env_file=None,
        openai_api_key=SecretStr(
            "sk-test-secret"
        ),
    )

    factory = OpenAIModelFactory(
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