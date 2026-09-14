from pathlib import Path

import pytest

from app.rag.parser import DocumentParseError, parse_markdown_document

VALID_DOCUMENT = """---
document_id: test-access
title: Test Access Procedure
category: access_control
version: "1.0"
priority: high
audience: security_staff
organization: Sentinel Facilities
document_type: procedure
---

## Objetivo

Este documento existe exclusivamente para probar el parser.
"""


def test_parses_valid_markdown_document(tmp_path: Path) -> None:
    document_path = tmp_path / "valid.md"
    document_path.write_text(
        VALID_DOCUMENT,
        encoding="utf-8",
    )

    document = parse_markdown_document(document_path)

    assert document.metadata.document_id == "test-access"
    assert document.metadata.title == "Test Access Procedure"
    assert document.metadata.category == "access_control"
    assert document.metadata.priority == "high"
    assert document.metadata.document_type == "procedure"
    assert "Este documento existe" in document.content
    assert document.source_path.endswith("valid.md")


def test_rejects_document_without_front_matter(tmp_path: Path) -> None:
    document_path = tmp_path / "missing-front-matter.md"
    document_path.write_text(
        "## Objetivo\n\nContenido sin metadata.",
        encoding="utf-8",
    )

    with pytest.raises(DocumentParseError):
        parse_markdown_document(document_path)


def test_rejects_document_with_empty_body(tmp_path: Path) -> None:
    document_path = tmp_path / "empty-body.md"
    document_path.write_text(
        """---
document_id: empty-body
title: Empty Body
category: access_control
version: "1.0"
priority: high
audience: security_staff
organization: Sentinel Facilities
document_type: procedure
---
""",
        encoding="utf-8",
    )

    with pytest.raises(DocumentParseError):
        parse_markdown_document(document_path)


def test_real_corpus_has_eight_unique_documents() -> None:
    document_paths = sorted(
        Path("data/documents").glob("*.md")
    )

    documents = [
        parse_markdown_document(path)
        for path in document_paths
    ]

    document_ids = {
        document.metadata.document_id
        for document in documents
    }

    assert len(document_paths) == 8
    assert len(documents) == 8
    assert len(document_ids) == 8

    for document in documents:
        assert document.content.strip()
        assert document.metadata.title.strip()
        assert document.metadata.category.strip()