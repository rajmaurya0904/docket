"""Tests for error handling and exit codes on bad input."""

from pathlib import Path

import pytest

from docket.builder import BuildError, SourceError, build
from docket.cli import EXIT_PROBLEMS, EXIT_USAGE, main


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_missing_source_raises_source_error(tmp_path: Path) -> None:
    with pytest.raises(SourceError, match="not found"):
        build(tmp_path / "missing", tmp_path / "out")


def test_source_that_is_a_file_raises(tmp_path: Path) -> None:
    write(tmp_path, "a.md", "# A")
    with pytest.raises(SourceError, match="not a directory"):
        build(tmp_path / "a.md", tmp_path / "out")


def test_empty_source_raises(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    with pytest.raises(SourceError, match="no Markdown files"):
        build(tmp_path / "docs", tmp_path / "out")


def test_source_with_only_non_markdown_raises(tmp_path: Path) -> None:
    write(tmp_path / "docs", "notes.txt", "hi")
    with pytest.raises(SourceError):
        build(tmp_path / "docs", tmp_path / "out")


def test_source_error_is_a_build_error() -> None:
    assert issubclass(SourceError, BuildError)


def test_output_inside_source_is_refused(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    write(src, "index.md", "# Home")
    with pytest.raises(BuildError, match="inside the source"):
        build(src, src / "site")


def test_output_equal_to_source_is_refused(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    write(src, "index.md", "# Home")
    with pytest.raises(BuildError, match="inside the source"):
        build(src, src)


def test_underscore_output_inside_source_is_allowed(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    write(src, "index.md", "# Home")
    build(src, src / "_site")
    assert (src / "_site" / "index.html").is_file()
    # a second build must not pick the generated output up as input
    result = build(src, src / "_site")
    assert [p.url for p in result.pages] == ["index.html"]


def test_output_containing_source_is_refused(tmp_path: Path) -> None:
    src = tmp_path / "out" / "docs"
    write(src, "index.md", "# Home")
    with pytest.raises(BuildError, match="contain the source"):
        build(src, tmp_path / "out")


def test_output_that_is_a_file_is_refused(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    write(src, "index.md", "# Home")
    write(tmp_path, "site", "i am a file")
    with pytest.raises(BuildError, match="not a directory"):
        build(src, tmp_path / "site")


def test_clean_refuses_a_directory_docket_did_not_create(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    write(src, "index.md", "# Home")
    precious = tmp_path / "precious"
    write(precious, "important.txt", "keep me")
    with pytest.raises(BuildError, match="refusing to clean"):
        build(src, precious, clean=True)
    assert (precious / "important.txt").read_text(encoding="utf-8") == "keep me"


def test_clean_allows_an_empty_existing_directory(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    write(src, "index.md", "# Home")
    (tmp_path / "site").mkdir()
    build(src, tmp_path / "site", clean=True)
    assert (tmp_path / "site" / "index.html").is_file()


def test_invalid_utf8_names_the_file(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    src.mkdir()
    (src / "bad.md").write_bytes(b"# Caf\xe9 \xff\xfe")
    with pytest.raises(BuildError, match=r"bad\.md: not valid UTF-8"):
        build(src, None)


def test_malformed_api_block_names_the_file(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    write(src, "api.md", "# API\n\n```api\nFETCH /x\n```\n")
    with pytest.raises(BuildError, match=r"api\.md: invalid api block"):
        build(src, None)


def test_cli_maps_source_errors_to_usage_exit_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["build", str(tmp_path / "missing")]) == EXIT_USAGE
    assert "error:" in capsys.readouterr().err


def test_cli_maps_build_errors_to_problem_exit_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "docs"
    write(src, "api.md", "```api\nnope\n```")
    assert main(["build", str(src), "-o", str(tmp_path / "o")]) == EXIT_PROBLEMS
    err = capsys.readouterr().err
    assert err.startswith("error: api.md: invalid api block")
    assert "Traceback" not in err


def test_failed_build_leaves_no_output(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    write(src, "api.md", "```api\nnope\n```")
    with pytest.raises(BuildError):
        build(src, tmp_path / "out")
    assert not (tmp_path / "out").exists()
