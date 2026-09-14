from pathlib import Path

import yaml
from pydantic import ValidationError

from app.models.document import DocumentMetadata, ParsedDocument


class DocumentParseError(ValueError):
    """Raised when a knowledge document cannot be parsed safely."""


def parse_markdown_document(path: str | Path) -> ParsedDocument:
    """Parse a Markdown document with YAML front matter."""

    source_path = Path(path)

    if not source_path.is_file():
        raise FileNotFoundError(
            f"Document not found: {source_path}"
        )

    raw_content = source_path.read_text(
        encoding="utf-8",
    ).removeprefix("\ufeff")

    lines = raw_content.splitlines()

    if not lines or lines[0].strip() != "---":
        raise DocumentParseError(
            f"Missing YAML front matter opening delimiter in {source_path}"
        )

    closing_index: int | None = None

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        raise DocumentParseError(
            f"Missing YAML front matter closing delimiter in {source_path}"
        )

    yaml_content = "\n".join(
        lines[1:closing_index]
    )

    markdown_body = "\n".join(
        lines[closing_index + 1 :]
    ).strip()

    if not markdown_body:
        raise DocumentParseError(
            f"Document body is empty in {source_path}"
        )

    try:
        raw_metadata = yaml.safe_load(yaml_content)
    except yaml.YAMLError as exc:
        raise DocumentParseError(
            f"Invalid YAML front matter in {source_path}"
        ) from exc

    if not isinstance(raw_metadata, dict):
        raise DocumentParseError(
            f"YAML front matter must contain a mapping in {source_path}"
        )

    try:
        metadata = DocumentMetadata.model_validate(
            raw_metadata
        )
    except ValidationError as exc:
        raise DocumentParseError(
            f"Invalid document metadata in {source_path}: {exc}"
        ) from exc

    return ParsedDocument(
        metadata=metadata,
        content=markdown_body,
        source_path=source_path.as_posix(),
    )