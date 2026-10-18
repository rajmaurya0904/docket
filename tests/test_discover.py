"""Tests for Markdown file discovery."""

from pathlib import Path

import pytest

from docket.discover import discover_markdown


def touch(root: Path, name: str, text: str = "x") -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_finds_nested_markdown(tmp_path: Path) -> None:
    touch(tmp_path, "index.md")
    touch(tmp_path, "guide/intro.md")
    touch(tmp_path, "guide/deep/more.md")
    found = discover_markdown(tmp_path)
    assert [p.as_posix() for p in found] == ["guide/deep/more.md", "guide/intro.md", "index.md"]


def test_empty_directory(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    assert discover_markdown(tmp_path) == []


def test_ignores_non_markdown(tmp_path: Path) -> None:
    touch(tmp_path, "a.md")
    touch(tmp_path, "b.txt")
    touch(tmp_path, "c.html")
    touch(tmp_path, "img/logo.png")
    assert discover_markdown(tmp_path) == [Path("a.md")]


def test_accepts_markdown_suffix_and_uppercase(tmp_path: Path) -> None:
    touch(tmp_path, "a.markdown")
    touch(tmp_path, "B.MD")
    assert {p.name for p in discover_markdown(tmp_path)} == {"a.markdown", "B.MD"}


def test_skips_hidden_and_underscore_paths(tmp_path: Path) -> None:
    touch(tmp_path, "keep.md")
    touch(tmp_path, ".git/notes.md")
    touch(tmp_path, "_drafts/wip.md")
    touch(tmp_path, "guide/_partial.md")
    assert discover_markdown(tmp_path) == [Path("keep.md")]


def test_results_are_relative(tmp_path: Path) -> None:
    touch(tmp_path, "x/y.md")
    (found,) = discover_markdown(tmp_path)
    assert not found.is_absolute()


def test_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        discover_markdown(tmp_path / "nope")


def test_file_instead_of_directory_raises(tmp_path: Path) -> None:
    touch(tmp_path, "a.md")
    with pytest.raises(NotADirectoryError):
        discover_markdown(tmp_path / "a.md")
