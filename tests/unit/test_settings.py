from pathlib import Path

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

def test_checkpoint_storage_path_resolves_relative_path() -> None:
    settings = Settings(
        _env_file=None,
        checkpoint_db_path=Path(".sentinel/test-checkpoints.sqlite"),
    )

    assert settings.checkpoint_storage_path.is_absolute()
    assert settings.checkpoint_storage_path.name == "test-checkpoints.sqlite"


def test_checkpoint_storage_path_preserves_absolute_path(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "custom-checkpoints.sqlite"
    )

    settings = Settings(
        _env_file=None,
        checkpoint_db_path=database_path,
    )

    assert settings.checkpoint_storage_path == database_path

def test_default_graph_recursion_limit_is_40() -> None:
    settings = Settings(
        _env_file=None,
    )

    assert settings.graph_recursion_limit == 40


def test_graph_recursion_limit_cannot_be_too_low() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            graph_recursion_limit=9,
        )

def test_langsmith_tracing_is_disabled_by_default() -> None:
    settings = Settings(
        _env_file=None,
    )

    assert settings.langsmith_tracing is False


def test_default_langsmith_project_is_sentinel_ai() -> None:
    settings = Settings(
        _env_file=None,
    )

    assert settings.langsmith_project == "sentinel-ai"
