"""Tests for the build orchestrator."""

import json
import re
from pathlib import Path

import pytest

from docket.builder import BuildError, build, prettify, relative_url, root_prefix


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    src = tmp_path / "docs"
    write(src, "index.md", "---\ntitle: Home\n---\n# Welcome\n\nSee [the guide](guide/intro.md).\n")
    write(
        src,
        "guide/intro.md",
        "---\ntitle: Intro\ndescription: Start here\norder: 1\n---\n"
        "# Intro\n\n## Setup\n\nBack to [home](../index.md) or [api](/api/users).\n",
    )
    write(
        src,
        "api/users.md",
        "# Users\n\n## GET /users/{id}\n\nFetch a user.\n\n### Response\n\n"
        '```json\n{"id": 1}\n```\n',
    )
    return src


def test_build_creates_pages_and_assets(docs: Path, tmp_path: Path) -> None:
    out = tmp_path / "site"
    result = build(docs, out, site_title="My Docs")
    assert (out / "index.html").is_file()
    assert (out / "guide" / "intro.html").is_file()
    assert (out / "api" / "users.html").is_file()
    assert (out / "assets" / "docket.css").is_file()
    assert (out / "assets" / "docket.js").is_file()
    assert (out / "assets" / "search-index.js").is_file()
    assert result.warnings == []
    assert result.files_written == 3 + 3
    assert result.endpoints == 1


def test_links_are_rewritten_relative_to_each_page(docs: Path, tmp_path: Path) -> None:
    build(docs, tmp_path / "site")
    index = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    intro = (tmp_path / "site" / "guide" / "intro.html").read_text(encoding="utf-8")
    assert 'href="guide/intro.html"' in index
    assert 'href="../index.html"' in intro
    assert 'href="../api/users.html"' in intro


def test_pages_use_relative_asset_paths(docs: Path, tmp_path: Path) -> None:
    build(docs, tmp_path / "site")
    intro = (tmp_path / "site" / "guide" / "intro.html").read_text(encoding="utf-8")
    index = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert 'href="../assets/docket.css"' in intro
    assert 'href="assets/docket.css"' in index


def test_title_and_description_come_from_frontmatter(docs: Path, tmp_path: Path) -> None:
    build(docs, tmp_path / "site", site_title="My Docs")
    intro = (tmp_path / "site" / "guide" / "intro.html").read_text(encoding="utf-8")
    assert "<title>Intro - My Docs</title>" in intro
    assert 'name="description" content="Start here"' in intro


def test_title_falls_back_to_h1_then_filename(tmp_path: Path) -> None:
    src = tmp_path / "d"
    write(src, "a.md", "# From Heading\n\ntext")
    write(src, "getting-started.md", "no heading here")
    result = build(src, None)
    titles = {p.source.name: p.title for p in result.pages}
    assert titles["a.md"] == "From Heading"
    assert titles["getting-started.md"] == "Getting Started"


def test_h1_is_added_when_the_page_has_none(tmp_path: Path) -> None:
    src = tmp_path / "d"
    write(src, "index.md", "---\ntitle: Plain & Simple\n---\njust text")
    build(src, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert "<h1>Plain &amp; Simple</h1>" in html


def test_api_section_gets_an_explorer_panel(docs: Path, tmp_path: Path) -> None:
    build(docs, tmp_path / "site")
    html = (tmp_path / "site" / "api" / "users.html").read_text(encoding="utf-8")
    assert 'class="endpoint"' in html
    assert 'id="get-usersid-try"' in html
    assert "data-endpoint=" in html
    assert 'class="method m-get">GET</span>' in html


def test_sidebar_groups_and_orders_pages(docs: Path, tmp_path: Path) -> None:
    build(docs, tmp_path / "site")
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert html.index("<h2>Api</h2>") < html.index("<h2>Guide</h2>")
    assert html.index(">Home</a>") < html.index(">Users</a>")


def test_order_frontmatter_sorts_within_a_group(tmp_path: Path) -> None:
    src = tmp_path / "d"
    write(src, "index.md", "# Home")
    write(src, "g/a.md", "---\ntitle: Alpha\norder: 2\n---\nx")
    write(src, "g/b.md", "---\ntitle: Beta\norder: 1\n---\nx")
    build(src, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert html.index(">Beta</a>") < html.index(">Alpha</a>")


def test_bad_order_value_is_a_warning(tmp_path: Path) -> None:
    src = tmp_path / "d"
    write(src, "index.md", "---\norder: first\n---\n# Home")
    result = build(src, None)
    assert any("'order' must be an integer" in w for w in result.warnings)


def test_index_is_generated_when_missing(tmp_path: Path) -> None:
    src = tmp_path / "d"
    write(src, "one.md", "# One")
    write(src, "sub/two.md", "# Two")
    build(src, tmp_path / "out", site_title="Site")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert "<h1" in html and "Site" in html
    assert 'href="one.html"' in html and 'href="sub/two.html"' in html


def test_broken_page_link_is_reported(tmp_path: Path) -> None:
    src = tmp_path / "d"
    write(src, "index.md", "[gone](nowhere.md) and [also](/missing/page)")
    result = build(src, None)
    assert len(result.warnings) == 2
    assert all("broken link" in w and "index.md" in w for w in result.warnings)


def test_missing_heading_fragment_is_reported(tmp_path: Path) -> None:
    src = tmp_path / "d"
    write(src, "index.md", "[ok](a.md#real) [bad](a.md#fake)")
    write(src, "a.md", "# A\n\n## Real\n")
    result = build(src, None)
    assert len(result.warnings) == 1
    assert "#fake" in result.warnings[0]


def test_external_and_anchor_links_are_untouched(tmp_path: Path) -> None:
    src = tmp_path / "d"
    write(src, "index.md", "[a](https://x.io/p) [b](#top) [c](mailto:a@b.co)\n\n## Top\n")
    result = build(src, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert result.warnings == []
    assert 'href="https://x.io/p"' in html and 'href="#top"' in html
    assert 'href="mailto:a@b.co"' in html


def test_link_climbing_above_root_is_reported(tmp_path: Path) -> None:
    src = tmp_path / "d"
    write(src, "index.md", "[up](../../etc.md)")
    result = build(src, None)
    assert "outside the documentation root" in result.warnings[0]


def test_static_files_are_copied_and_links_to_them_work(tmp_path: Path) -> None:
    src = tmp_path / "d"
    write(src, "guide/page.md", "![pic](img/logo.svg) [file](../files/data.csv)")
    write(src, "guide/img/logo.svg", "<svg/>")
    write(src, "files/data.csv", "a,b")
    write(src, "_private/secret.txt", "no")
    result = build(src, tmp_path / "out")
    out = tmp_path / "out"
    assert (out / "guide" / "img" / "logo.svg").is_file()
    assert (out / "files" / "data.csv").is_file()
    assert not (out / "_private").exists()
    assert result.warnings == []


def test_search_index_is_valid_javascript_data(docs: Path, tmp_path: Path) -> None:
    build(docs, tmp_path / "site")
    script = (tmp_path / "site" / "assets" / "search-index.js").read_text(encoding="utf-8")
    payload = re.fullmatch(r"window\.DOCKET_INDEX = (.*);\n", script, re.S)
    assert payload
    entries = json.loads(payload.group(1))
    assert {e["url"] for e in entries} == {"index.html", "guide/intro.html", "api/users.html"}
    assert any("Fetch a user." in e["text"] for e in entries)


def test_search_can_be_disabled(docs: Path, tmp_path: Path) -> None:
    build(docs, tmp_path / "site", search=False)
    assert not (tmp_path / "site" / "assets" / "search-index.js").exists()
    assert "search-index.js" not in (tmp_path / "site" / "index.html").read_text(encoding="utf-8")


def test_base_url_is_embedded(docs: Path, tmp_path: Path) -> None:
    build(docs, tmp_path / "site", base_url="https://api.example.com")
    html = (tmp_path / "site" / "api" / "users.html").read_text(encoding="utf-8")
    assert 'name="docket-base-url" content="https://api.example.com"' in html


def test_invalid_json_example_is_a_warning(tmp_path: Path) -> None:
    src = tmp_path / "d"
    write(src, "index.md", "## GET /x\n\n### Response\n\n```json\n{bad\n```\n")
    result = build(src, None)
    assert any("not valid JSON" in w for w in result.warnings)


def test_dry_run_writes_nothing(docs: Path, tmp_path: Path) -> None:
    result = build(docs, None)
    assert result.output is None and result.files_written == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["docs"]


def test_rebuild_overwrites_and_clean_removes_stale_files(docs: Path, tmp_path: Path) -> None:
    out = tmp_path / "site"
    build(docs, out)
    (out / "stale.html").write_text("old", encoding="utf-8")
    build(docs, out)
    assert (out / "stale.html").exists()
    build(docs, out, clean=True)
    assert not (out / "stale.html").exists()
    assert (out / "index.html").exists()


def test_two_sources_mapping_to_one_url_is_an_error(tmp_path: Path) -> None:
    src = tmp_path / "d"
    write(src, "a.md", "# A")
    write(src, "a.markdown", "# A2")
    with pytest.raises(BuildError, match="both write a.html"):
        build(src, None)


def test_url_helpers() -> None:
    assert relative_url("guide/intro.html", "index.html") == "guide/intro.html"
    assert relative_url("index.html", "guide/intro.html") == "../index.html"
    assert relative_url("guide/b.html", "guide/a.html") == "b.html"
    assert relative_url("api/x.html", "guide/a.html") == "../api/x.html"
    assert root_prefix("index.html") == ""
    assert root_prefix("a/b/c.html") == "../../"
    assert prettify("getting-started_now") == "Getting Started Now"
