"""Tests for the bundled CSS and client-side script."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from docket.assets import ASSET_FILES, CSS, JS, write_assets

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")


def test_write_assets_creates_files(tmp_path: Path) -> None:
    written = write_assets(tmp_path / "site")
    assert sorted(p.relative_to(tmp_path / "site").as_posix() for p in written) == [
        "assets/docket.css",
        "assets/docket.js",
    ]
    assert all(p.is_file() and p.stat().st_size > 500 for p in written)


def test_written_content_matches_bundle(tmp_path: Path) -> None:
    write_assets(tmp_path)
    for relative, content in ASSET_FILES.items():
        assert (tmp_path / relative).read_text(encoding="utf-8") == content


def test_written_files_use_unix_newlines(tmp_path: Path) -> None:
    write_assets(tmp_path)
    assert b"\r\n" not in (tmp_path / "assets" / "docket.js").read_bytes()


def test_write_assets_is_idempotent(tmp_path: Path) -> None:
    write_assets(tmp_path)
    write_assets(tmp_path)
    assert len(list((tmp_path / "assets").iterdir())) == 2


def test_stylesheet_has_dark_mode_and_mobile_rules() -> None:
    assert "prefers-color-scheme: dark" in CSS
    assert "max-width: 44rem" in CSS
    assert CSS.count("{") == CSS.count("}")


def test_script_exposes_explorer_hooks() -> None:
    for name in ("buildUrl", "buildCurl", "initExplorer", "DOCKET_INDEX"):
        assert name in JS


def run_node(tmp_path: Path, snippet: str) -> str:
    script = tmp_path / "docket.js"
    script.write_text(JS, encoding="utf-8", newline="\n")
    code = f"const d = require({json.dumps(script.as_posix())});\n{snippet}"
    proc = subprocess.run(
        [NODE, "-e", code], capture_output=True, text=True, check=False, timeout=30
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


@needs_node
def test_script_is_valid_javascript(tmp_path: Path) -> None:
    script = tmp_path / "docket.js"
    script.write_text(JS, encoding="utf-8", newline="\n")
    proc = subprocess.run([NODE, "--check", str(script)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


@needs_node
def test_build_url_substitutes_and_encodes(tmp_path: Path) -> None:
    out = run_node(
        tmp_path,
        """
const ep = {path: '/users/{id}', params: [
  {name: 'id', location: 'path', required: true},
  {name: 'q', location: 'query'}, {name: 'tag', location: 'query'}]};
console.log(d.buildUrl('http://h.io/', ep, {id: 'a b', q: '1&2', tag: ''}));
""",
    )
    assert out == "http://h.io/users/a%20b?q=1%262"


@needs_node
def test_build_url_requires_path_params(tmp_path: Path) -> None:
    out = run_node(
        tmp_path,
        """
const ep = {path: '/users/{id}', params: [{name: 'id', location: 'path', required: true}]};
try { d.buildUrl('http://h.io', ep, {}); } catch (e) { console.log(e.message); }
""",
    )
    assert out == "Missing path parameter: id"


@needs_node
def test_build_headers_and_curl(tmp_path: Path) -> None:
    out = run_node(
        tmp_path,
        """
const ep = {method: 'POST', path: '/x', headers: {Authorization: 'Bearer t'},
  params: [{name: 'X-Trace', location: 'header'}]};
const h = d.buildHeaders(ep, {'X-Trace': 'abc'}, '{"a":1}');
console.log(JSON.stringify(h));
console.log(d.buildCurl('http://h.io/x', 'POST', h, '{"it\\'s":1}'));
""",
    )
    first, second = out.splitlines()
    assert json.loads(first) == {
        "Authorization": "Bearer t",
        "X-Trace": "abc",
        "Content-Type": "application/json",
    }
    assert second.startswith("curl -X POST -H 'Authorization: Bearer t'")
    assert "-d '{\"it'\\''s\":1}'" in second


@needs_node
def test_pretty_body_formats_json_only(tmp_path: Path) -> None:
    out = run_node(
        tmp_path,
        """
console.log(JSON.stringify([d.prettyBody('{"a":1}', 'application/json'), d.prettyBody('hi', '')]));
""",
    )
    assert json.loads(out) == ['{\n  "a": 1\n}', "hi"]
