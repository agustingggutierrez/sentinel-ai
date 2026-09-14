from functools import lru_cache

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config.settings import Settings, get_settings


class OpenAIConfigurationError(RuntimeError):
    """Raised when OpenAI configuration is missing or invalid."""


class OpenAIModelFactory:
    """Create configured OpenAI chat and structured-output models."""

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings

    def create_chat_model(
        self,
    ) -> ChatOpenAI:
        """Create a ChatOpenAI instance from application settings."""

        api_key = self.settings.openai_api_key

        if api_key is None:
            raise OpenAIConfigurationError(
                "OPENAI_API_KEY is required to create the OpenAI model."
            )

        secret_value = api_key.get_secret_value().strip()

        if not secret_value:
            raise OpenAIConfigurationError(
                "OPENAI_API_KEY cannot be blank."
            )

        return ChatOpenAI(
            model=self.settings.openai_model,
            api_key=secret_value,
        )

    def create_structured_model(
        self,
        schema: type[BaseModel],
    ):
        """Create a model constrained to a Pydantic output schema."""

        model = self.create_chat_model()

        return model.with_structured_output(
            schema,
            method="json_schema",
            strict=True,
        )


@lru_cache
def get_openai_model_factory() -> OpenAIModelFactory:
    """Return the cached OpenAI model factory."""

    return OpenAIModelFactory(
        get_settings()
    )