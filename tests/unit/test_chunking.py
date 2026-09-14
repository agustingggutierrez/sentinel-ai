from pathlib import Path

import pytest

from app.rag.chunking import (
    build_document_chunks,
    split_long_section,
)
from app.rag.parser import parse_markdown_document


def test_long_section_split_respects_size_and_overlap() -> None:
    words = [
        f"word-{index}"
        for index in range(55)
    ]

    content = " ".join(words)

    parts = split_long_section(
        content,
        max_words=20,
        overlap_words=5,
    )

    assert len(parts) == 4

    tokenized_parts = [
        part.split()
        for part in parts
    ]

    assert all(
        len(part) <= 20
        for part in tokenized_parts
    )

    assert (
        tokenized_parts[0][-5:]
        == tokenized_parts[1][:5]
    )

    assert (
        tokenized_parts[1][-5:]
        == tokenized_parts[2][:5]
    )


def test_long_section_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError):
        split_long_section(
            "one two three four five",
            max_words=5,
            overlap_words=5,
        )


def test_chunk_ids_are_deterministic() -> None:
    path = Path("data/documents/01_access_control.md")

    document = parse_markdown_document(path)

    first_run = build_document_chunks(document)
    second_run = build_document_chunks(document)

    first_ids = [
        chunk.chunk_id
        for chunk in first_run
    ]

    second_ids = [
        chunk.chunk_id
        for chunk in second_run
    ]

    assert first_ids == second_ids


def test_real_corpus_generates_154_unique_chunks() -> None:
    all_chunks = []

    for path in sorted(
        Path("data/documents").glob("*.md")
    ):
        document = parse_markdown_document(path)

        all_chunks.extend(
            build_document_chunks(document)
        )

    chunk_ids = {
        chunk.chunk_id
        for chunk in all_chunks
    }

    assert len(all_chunks) == 154
    assert len(chunk_ids) == 154


def test_chunks_preserve_document_metadata() -> None:
    path = Path("data/documents/07_restricted_areas.md")

    document = parse_markdown_document(path)
    chunks = build_document_chunks(document)

    assert chunks

    for chunk in chunks:
        assert chunk.document_id == document.metadata.document_id
        assert chunk.title == document.metadata.title
        assert chunk.category == document.metadata.category
        assert chunk.version == document.metadata.version
        assert chunk.priority == document.metadata.priority
        assert chunk.document_type == document.metadata.document_type
        assert chunk.section.strip()
        assert chunk.content.strip()
        assert chunk.source_path.endswith(
            "07_restricted_areas.md"
        )