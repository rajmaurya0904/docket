"""Tests for the command-line interface."""

import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from docket import __version__
from docket.cli import EXIT_OK, EXIT_PROBLEMS, EXIT_USAGE, main, make_parser


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    src = tmp_path / "docs"
    write(src, "index.md", "# Home\n\nSee [guide](guide.md).\n")
    write(src, "guide.md", "# Guide\n\n## GET /ping\n\nPing.\n")
    return src


def test_help_exits_zero_and_lists_commands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for word in ("build", "check", "serve", "usage:"):
        assert word in out


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"docket {__version__}"


def test_no_command_prints_help_and_returns_usage_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([]) == EXIT_USAGE
    assert "usage:" in capsys.readouterr().err


def test_build_subcommand_requires_a_source() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["build"])
    assert exc.value.code == 2


def test_unknown_option_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["build", "docs", "--nope"])
    assert exc.value.code == 2


def test_build_parses_all_flags() -> None:
    args = make_parser().parse_args(
        [
            "build",
            "docs",
            "-o",
            "out",
            "-t",
            "Mine",
            "--base-url",
            "https://api.x.io",
            "--clean",
            "--no-search",
            "--strict",
        ]
    )
    assert args.source == Path("docs") and args.output == Path("out")
    assert args.title == "Mine" and args.base_url == "https://api.x.io"
    assert args.clean and args.no_search and args.strict


def test_build_defaults() -> None:
    args = make_parser().parse_args(["build", "docs"])
    assert args.output == Path("site") and args.title == "Documentation"
    assert not args.clean and not args.no_search and not args.strict


def test_build_writes_site_and_summarises(
    docs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "site"
    assert main(["build", str(docs), "-o", str(out), "-t", "T"]) == EXIT_OK
    captured = capsys.readouterr()
    assert "2 pages, 1 API endpoint, 0 warnings" in captured.out
    assert "guide.md" in captured.out and "guide.html" in captured.out
    assert (out / "index.html").is_file() and (out / "guide.html").is_file()


def test_missing_source_is_a_clean_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["build", str(tmp_path / "nope"), "-o", str(tmp_path / "o")])
    assert code == EXIT_USAGE
    err = capsys.readouterr().err
    assert err.startswith("error: source directory not found")
    assert "Traceback" not in err
    assert not (tmp_path / "o").exists()


def test_warnings_go_to_stderr_and_do_not_fail_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "d"
    write(src, "index.md", "[x](missing.md)")
    assert main(["build", str(src), "-o", str(tmp_path / "o")]) == EXIT_OK
    captured = capsys.readouterr()
    assert "warning: index.md: broken link 'missing.md'" in captured.err
    assert "1 warning" in captured.out


def test_strict_turns_warnings_into_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "d"
    write(src, "index.md", "[x](missing.md)")
    assert main(["build", str(src), "-o", str(tmp_path / "o"), "--strict"]) == EXIT_PROBLEMS
    assert "--strict" in capsys.readouterr().err


def test_check_is_a_dry_run(docs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    before = sorted(p.name for p in tmp_path.iterdir())
    assert main(["check", str(docs)]) == EXIT_OK
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    assert "2 pages, 1 API endpoint, 0 warnings" in capsys.readouterr().out


def test_check_fails_on_warnings(tmp_path: Path) -> None:
    src = tmp_path / "d"
    write(src, "index.md", "[x](missing.md)")
    assert main(["check", str(src)]) == EXIT_PROBLEMS


def test_serve_rejects_a_directory_that_is_not_a_built_site(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["serve", str(tmp_path)]) == EXIT_USAGE
    assert "not a built site" in capsys.readouterr().err


def test_serve_rejects_a_bad_port(docs: Path, tmp_path: Path) -> None:
    out = tmp_path / "site"
    main(["build", str(docs), "-o", str(out)])
    assert main(["serve", str(out), "-p", "70000"]) == EXIT_USAGE


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_serve_serves_the_built_site(docs: Path, tmp_path: Path) -> None:
    out = tmp_path / "site"
    main(["build", str(docs), "-o", str(out)])
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "docket", "serve", str(out), "-p", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        body = None
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/guide.html", timeout=2) as r:
                    body = r.read().decode("utf-8")
                break
            except OSError:
                time.sleep(0.2)
        assert body is not None and "<h1" in body and "GET /ping" in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_python_dash_m_entry_point() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "docket", "--version"], capture_output=True, text=True, timeout=30
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == f"docket {__version__}"
