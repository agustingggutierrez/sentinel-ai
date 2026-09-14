from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "SentinelAI"
    app_env: Literal["development", "test", "production"] = "development"

    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)

    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    openai_api_key: SecretStr | None = None

    openai_model: str = Field(
        default="gpt-5.6-luna",
        min_length=1,
        max_length=128,
    )

    qdrant_mode: Literal["local", "server"] = "local"

    qdrant_local_path: Path = Path(".qdrant")

    qdrant_url: str = "http://localhost:6333"

    qdrant_api_key: str | None = None

    qdrant_collection_name: str = Field(
        default="sentinel_ai_documents",
        min_length=1,
        max_length=128,
    )

    dense_embedding_model: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    sparse_embedding_model: str = "Qdrant/bm25"

    rerank_model: str = "answerdotai/answerai-colbert-small-v1"

    dense_prefetch_limit: int = Field(
        default=12,
        ge=1,
        le=100,
    )

    sparse_prefetch_limit: int = Field(
        default=12,
        ge=1,
        le=100,
    )

    retrieval_candidate_limit: int = Field(
        default=15,
        ge=1,
        le=100,
    )

    retrieval_top_k: int = Field(
        default=5,
        ge=1,
        le=50,
    )

    retrieval_strategy: Literal[
        "rrf",
        "colbert",
    ] = "rrf"

    ingestion_batch_size: int = Field(
        default=8,
        ge=1,
        le=64,
    )

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_retrieval_limits(self) -> Self:
        """Ensure the final top-k does not exceed the candidate pool."""

        if self.retrieval_top_k > self.retrieval_candidate_limit:
            raise ValueError(
                "RETRIEVAL_TOP_K cannot be greater than "
                "RETRIEVAL_CANDIDATE_LIMIT."
            )

        return self

    @property
    def qdrant_storage_path(self) -> Path:
        """Return the absolute local Qdrant storage path."""

        if self.qdrant_local_path.is_absolute():
            return self.qdrant_local_path

        return PROJECT_ROOT / self.qdrant_local_path


@lru_cache
def get_settings() -> Settings:
    """Return a cached application settings instance."""
    return Settings()