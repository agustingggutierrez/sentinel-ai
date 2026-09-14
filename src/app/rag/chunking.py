import re
import unicodedata
from dataclasses import dataclass

from app.models.chunk import DocumentChunk
from app.models.document import ParsedDocument


MAX_CHUNK_WORDS = 90
CHUNK_OVERLAP_WORDS = 15


class ChunkingError(ValueError):
    """Raised when a parsed document cannot be split into semantic chunks."""


@dataclass(frozen=True, slots=True)
class MarkdownSection:
    """A level-two Markdown section extracted from a parsed document."""

    title: str
    content: str


def split_document_sections(
    document: ParsedDocument,
) -> list[MarkdownSection]:
    """Split a parsed Markdown document using level-two headings."""

    sections: list[MarkdownSection] = []

    current_title: str | None = None
    current_lines: list[str] = []

    for line in document.content.splitlines():
        if line.startswith("## "):
            if current_title is not None:
                _append_section(
                    sections=sections,
                    title=current_title,
                    lines=current_lines,
                    document_id=document.metadata.document_id,
                )

            current_title = line[3:].strip()
            current_lines = []

            if not current_title:
                raise ChunkingError(
                    "Empty level-two heading found in "
                    f"{document.metadata.document_id}"
                )

            continue

        if current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        _append_section(
            sections=sections,
            title=current_title,
            lines=current_lines,
            document_id=document.metadata.document_id,
        )

    if not sections:
        raise ChunkingError(
            "No level-two Markdown sections found in "
            f"{document.metadata.document_id}"
        )

    return sections


def slugify_section_title(title: str) -> str:
    """Convert a section title into a deterministic ASCII slug."""

    normalized = unicodedata.normalize("NFKD", title)

    ascii_text = normalized.encode(
        "ascii",
        "ignore",
    ).decode("ascii")

    lowercase = ascii_text.lower()

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        lowercase,
    ).strip("-")

    if not slug:
        raise ChunkingError(
            f"Cannot generate a slug from section title: {title!r}"
        )

    return slug


def build_chunk_id(
    *,
    document_id: str,
    section_title: str,
    chunk_index: int,
    section_part: int | None = None,
) -> str:
    """Build a deterministic and human-readable chunk identifier."""

    if chunk_index < 0:
        raise ChunkingError("chunk_index cannot be negative")

    document_slug = slugify_section_title(document_id)
    section_slug = slugify_section_title(section_title)

    chunk_id = (
        f"{document_slug}::"
        f"{chunk_index:03d}::"
        f"{section_slug}"
    )

    if section_part is not None:
        chunk_id += f"::part-{section_part:02d}"

    return chunk_id


def split_long_section(
    content: str,
    *,
    max_words: int = MAX_CHUNK_WORDS,
    overlap_words: int = CHUNK_OVERLAP_WORDS,
) -> list[str]:
    """Split an oversized section using a bounded word window."""

    if max_words <= 0:
        raise ChunkingError("max_words must be greater than zero")

    if overlap_words < 0:
        raise ChunkingError("overlap_words cannot be negative")

    if overlap_words >= max_words:
        raise ChunkingError(
            "overlap_words must be smaller than max_words"
        )

    words = content.split()

    if len(words) <= max_words:
        return [content.strip()]

    parts: list[str] = []
    start = 0

    while start < len(words):
        end = min(start + max_words, len(words))
        part = " ".join(words[start:end]).strip()

        if part:
            parts.append(part)

        if end == len(words):
            break

        start = end - overlap_words

    return parts


def build_document_chunks(
    document: ParsedDocument,
) -> list[DocumentChunk]:
    """Create validated semantic chunks from a parsed document."""

    sections = split_document_sections(document)
    chunks: list[DocumentChunk] = []
    chunk_index = 0

    for section in sections:
        parts = split_long_section(section.content)
        is_split = len(parts) > 1

        for part_number, part in enumerate(parts, start=1):
            chunk_id = build_chunk_id(
                document_id=document.metadata.document_id,
                section_title=section.title,
                chunk_index=chunk_index,
                section_part=part_number if is_split else None,
            )

            chunk_content = (
                f"## {section.title}\n\n"
                f"{part}"
            )

            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document.metadata.document_id,
                    title=document.metadata.title,
                    category=document.metadata.category,
                    version=document.metadata.version,
                    priority=document.metadata.priority,
                    document_type=document.metadata.document_type,
                    section=section.title,
                    chunk_index=chunk_index,
                    content=chunk_content,
                    source_path=document.source_path,
                )
            )

            chunk_index += 1

    return chunks


def _append_section(
    *,
    sections: list[MarkdownSection],
    title: str,
    lines: list[str],
    document_id: str,
) -> None:
    """Validate and append one semantic Markdown section."""

    content = "\n".join(lines).strip()

    if not content:
        raise ChunkingError(
            f"Section '{title}' is empty in {document_id}"
        )

    sections.append(
        MarkdownSection(
            title=title,
            content=content,
        )
    )