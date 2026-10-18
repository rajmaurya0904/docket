"""Find the Markdown files that make up a documentation tree."""

from __future__ import annotations

from pathlib import Path

MARKDOWN_SUFFIXES = {".md", ".markdown"}


def is_hidden(relative: Path) -> bool:
    """Return True if any component of ``relative`` starts with a dot or underscore."""
    return any(part.startswith((".", "_")) for part in relative.parts)


def discover_markdown(source: Path) -> list[Path]:
    """Return every Markdown file under ``source``, relative to it, sorted.

    Files and directories whose name starts with ``.`` or ``_`` are skipped, so
    ``.git`` or a ``_drafts`` folder never leak into the site. Raises
    ``NotADirectoryError`` if ``source`` is not a directory.
    """
    source = Path(source)
    if not source.is_dir():
        raise NotADirectoryError(f"not a directory: {source}")
    found: list[Path] = []
    for path in source.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in MARKDOWN_SUFFIXES:
            continue
        relative = path.relative_to(source)
        if is_hidden(relative):
            continue
        found.append(relative)
    return sorted(found, key=lambda p: p.as_posix().lower())
