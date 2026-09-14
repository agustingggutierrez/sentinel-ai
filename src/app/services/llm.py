from functools import lru_cache

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config.settings import Settings, get_settings


class LLMConfigurationError(RuntimeError):
    """Raised when the configured LLM provider is missing credentials."""


class LLMModelFactory:
    """Create provider-specific chat and structured-output models."""

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings

    def create_chat_model(
        self,
    ):
        """Create the configured chat model."""

        if self.settings.llm_provider == "groq":
            return self._create_groq_model()

        if self.settings.llm_provider == "openai":
            return self._create_openai_model()

        raise LLMConfigurationError(
            f"Unsupported LLM provider: {self.settings.llm_provider}"
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

    def _create_groq_model(
        self,
    ) -> ChatGroq:
        api_key = self.settings.groq_api_key

        if api_key is None:
            raise LLMConfigurationError(
                "GROQ_API_KEY is required when LLM_PROVIDER=groq."
            )

        secret_value = api_key.get_secret_value().strip()

        if not secret_value:
            raise LLMConfigurationError(
                "GROQ_API_KEY cannot be blank."
            )

        return ChatGroq(
            model=self.settings.groq_model,
            api_key=secret_value,
            temperature=0,
        )

    def _create_openai_model(
        self,
    ) -> ChatOpenAI:
        api_key = self.settings.openai_api_key

        if api_key is None:
            raise LLMConfigurationError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai."
            )

        secret_value = api_key.get_secret_value().strip()

        if not secret_value:
            raise LLMConfigurationError(
                "OPENAI_API_KEY cannot be blank."
            )

        return ChatOpenAI(
            model=self.settings.openai_model,
            api_key=secret_value,
        )


OpenAIConfigurationError = LLMConfigurationError
OpenAIModelFactory = LLMModelFactory


@lru_cache
def get_llm_model_factory() -> LLMModelFactory:
    """Return the cached configured LLM model factory."""

    return LLMModelFactory(
        get_settings()
    )


def get_openai_model_factory() -> LLMModelFactory:
    """Backward-compatible alias for the model factory."""

    return get_llm_model_factory()