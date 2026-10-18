"""Tests for the page template and the endpoint panel."""

import html
import json
import re

from docket.api_parser import Endpoint, Param, Response, parse_api_block
from docket.explorer import endpoint_data, render_explorer
from docket.template import NavGroup, NavItem, TocEntry, render_nav, render_page, render_toc

NAV = [
    NavGroup("", [NavItem("Home", "index.html")]),
    NavGroup("Guide", [NavItem("Intro", "guide/intro.html"), NavItem("Setup", "guide/setup.html")]),
]


def page(**overrides) -> str:
    args = {
        "site_title": "Docs",
        "page_title": "Intro",
        "body_html": "<h1>Intro</h1>",
        "nav": NAV,
        "current": "guide/intro.html",
        "root": "../",
    }
    args.update(overrides)
    return render_page(**args)


def test_page_is_a_complete_document() -> None:
    out = page()
    assert out.startswith("<!doctype html>")
    assert out.rstrip().endswith("</html>")
    assert "<main>\n<h1>Intro</h1>\n</main>" in out


def test_title_combines_page_and_site() -> None:
    assert "<title>Intro - Docs</title>" in page()
    assert "<title>Docs</title>" in page(page_title="Docs")


def test_titles_are_escaped() -> None:
    out = page(site_title="A & <B>", page_title='x"y')
    assert "A &amp; &lt;B&gt;" in out
    assert "<B>" not in out


def test_asset_links_use_the_relative_root() -> None:
    out = page(root="../../")
    assert 'href="../../assets/docket.css"' in out
    assert 'src="../../assets/docket.js"' in out
    assert 'data-root="../../"' in out


def test_nav_marks_current_page_and_prefixes_root() -> None:
    nav = render_nav(NAV, "guide/intro.html", "../")
    assert '<a href="../guide/intro.html" aria-current="page">Intro</a>' in nav
    assert '<a href="../guide/setup.html">Setup</a>' in nav
    assert "<h2>Guide</h2>" in nav
    assert nav.count("<h2>") == 1  # the ungrouped section has no heading


def test_toc_lists_h2_and_h3_only() -> None:
    entries = [
        TocEntry(1, "Title", "title"),
        TocEntry(2, "One", "one"),
        TocEntry(3, "Sub", "sub"),
        TocEntry(4, "Deep", "deep"),
    ]
    out = render_toc(entries)
    assert 'href="#one"' in out and 'class="l3"' in out
    assert "title" not in out and "deep" not in out


def test_toc_omitted_for_short_pages() -> None:
    assert render_toc([TocEntry(2, "Only", "only")]) == ""
    assert "On this page" not in page()


def test_meta_tags_only_when_given() -> None:
    plain = page()
    assert "docket-base-url" not in plain and 'name="description"' not in plain
    rich = page(description="About <it>", base_url="https://api.example.com")
    assert 'content="About &lt;it&gt;"' in rich
    assert 'name="docket-base-url" content="https://api.example.com"' in rich


def test_search_box_and_index_script_are_optional() -> None:
    assert "search-index.js" not in page()
    on = page(search_index=True)
    assert 'src="../assets/search-index.js"' in on
    assert 'class="search"' in on


def test_panel_for_heading_endpoint_is_minimal() -> None:
    ep = Endpoint("GET", "/users/{id}", anchor="get-usersid", summary="Fetch.")
    ep.params.append(Param("id", "path", "integer", True))
    out = render_explorer(ep)
    assert 'id="get-usersid-try"' in out
    assert '<span class="method m-get">GET</span>' in out
    assert "<code>/users/{id}</code>" in out
    assert "<table>" not in out and "Fetch." not in out


def test_panel_data_attribute_round_trips() -> None:
    ep = Endpoint(
        "POST",
        "/x",
        anchor="post-x",
        request_body='{"a": "<&>"}',
        responses=[Response("201", '{"ok": true}')],
        headers={"X-Key": "v"},
    )
    out = render_explorer(ep)
    raw = re.search(r'data-endpoint="([^"]*)"', out).group(1)
    assert json.loads(html.unescape(raw)) == endpoint_data(ep)
    assert endpoint_data(ep)["responses"] == [{"status": "201", "body": '{"ok": true}'}]
    assert "<&>" not in out


def test_panel_for_api_fence_documents_everything() -> None:
    ep = parse_api_block(
        "POST /items\nsummary: Create an *item*\nparam dry_run query boolean: Validate only\n"
        'body:\n  {"name": "x"}\nresponse 201:\n  {"id": 1}\n'
    )
    out = render_explorer(ep)
    assert "<em>item</em>" in out
    assert "<code>dry_run</code>" in out and "Validate only" in out
    assert "<h4>Request body</h4>" in out
    assert "<h4>Response 201</h4>" in out
    assert out.count("<pre>") == 2


def test_panel_escapes_untrusted_fields() -> None:
    ep = Endpoint("GET", '/a"><script>', anchor="x")
    out = render_explorer(ep)
    assert "<script>" not in out
