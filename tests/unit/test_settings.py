import pytest
from pydantic import ValidationError

from app.config.settings import Settings


def test_default_retrieval_strategy_is_rrf() -> None:
    settings = Settings(
        _env_file=None,
    )

    assert settings.retrieval_strategy == "rrf"


def test_colbert_is_a_valid_retrieval_strategy() -> None:
    settings = Settings(
        _env_file=None,
        retrieval_strategy="colbert",
    )

    assert settings.retrieval_strategy == "colbert"


def test_invalid_retrieval_strategy_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            retrieval_strategy="magic",
        )


def test_top_k_cannot_exceed_candidate_limit() -> None:
    with pytest.raises(
        ValidationError,
        match="RETRIEVAL_TOP_K cannot be greater",
    ):
        Settings(
            _env_file=None,
            retrieval_top_k=16,
            retrieval_candidate_limit=15,
        )


def test_ingestion_batch_size_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            ingestion_batch_size=0,
        )