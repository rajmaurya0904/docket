"""A small frontmatter parser: flat ``key: value`` metadata between ``---`` fences."""

from __future__ import annotations


def _unquote(value: str) -> str:
    """Strip one pair of matching single or double quotes around ``value``."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(markdown: str) -> tuple[dict[str, str], str]:
    """Split ``markdown`` into ``(metadata, body)``.

    Frontmatter must start on the very first line with ``---`` and end at the next
    line that is only ``---``. Each metadata line is ``key: value`` (split on the
    first colon, so values may contain colons); matching quotes around a value are
    removed, lines starting with ``#`` are comments, and lines without a colon are
    ignored. Nested YAML is not supported. If there is no opening fence, or the
    fence is never closed, the input is returned unchanged with empty metadata.
    """
    if markdown.startswith("﻿"):
        markdown = markdown[1:]
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, markdown

    closing = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), -1)
    if closing == -1:
        return {}, markdown

    metadata: dict[str, str] = {}
    for line in lines[1:closing]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key:
            metadata[key] = _unquote(value.strip())

    return metadata, "\n".join(lines[closing + 1 :])
