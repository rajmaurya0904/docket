"""Build the bundled examples/ project through the CLI and inspect the output."""

import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.hrefs: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self.hrefs.append(attributes["href"])
        if attributes.get("id"):
            self.ids.add(attributes["id"])


def parse_html(path: Path) -> Collector:
    collector = Collector()
    collector.feed(path.read_text(encoding="utf-8"))
    return collector


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, subprocess.CompletedProcess]:
    out = tmp_path_factory.mktemp("example") / "site"
    proc = subprocess.run(
        [sys.executable, "-m", "docket", "build", str(EXAMPLES), "-o", str(out), "--strict"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return out, proc


def test_build_succeeds_with_no_warnings(site) -> None:
    _, proc = site
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    assert "4 pages, 3 API endpoints, 0 warnings" in proc.stdout


def test_expected_files_exist(site) -> None:
    out, _ = site
    for name in (
        "index.html",
        "api/users.html",
        "api/health.html",
        "guide/introduction.html",
        "assets/docket.css",
        "assets/docket.js",
        "assets/search-index.js",
    ):
        assert (out / name).is_file(), name


def test_every_internal_link_resolves(site) -> None:
    out, _ = site
    checked = 0
    for page in out.rglob("*.html"):
        for href in parse_html(page).hrefs:
            if re.match(r"^([a-z]+:|#|//)", href):
                continue
            target = (page.parent / href.split("#")[0]).resolve()
            assert target.exists(), f"{page.name} links to missing {href}"
            checked += 1
    assert checked > 10


def test_every_anchor_link_has_a_target(site) -> None:
    out, _ = site
    for page in out.rglob("*.html"):
        parsed = parse_html(page)
        for href in parsed.hrefs:
            if href.startswith("#"):
                assert href[1:] in parsed.ids, f"{page.name}: {href}"


def test_users_page_has_both_endpoint_panels(site) -> None:
    out, _ = site
    html = (out / "api" / "users.html").read_text(encoding="utf-8")
    assert html.count('class="endpoint"') == 2
    assert 'id="get-users-try"' in html and 'id="post-users-try"' in html
    assert '"method":"POST"' in html.replace("&quot;", '"')


def test_api_block_page_documents_the_endpoint(site) -> None:
    out, _ = site
    html = (out / "api" / "health.html").read_text(encoding="utf-8")
    assert "Returns <code>ok</code> while the service is up." in html
    assert "<h4>Response 503</h4>" in html
    assert "dependency status" in html


def test_pages_load_the_script_and_stylesheet_relatively(site) -> None:
    out, _ = site
    assert 'src="../assets/docket.js"' in (out / "api" / "users.html").read_text(encoding="utf-8")
    assert 'src="assets/docket.js"' in (out / "index.html").read_text(encoding="utf-8")


def test_html_is_well_formed_enough_to_have_one_main_per_page(site) -> None:
    out, _ = site
    for page in out.rglob("*.html"):
        tags = parse_html(page).tags
        assert tags.count("main") == 1 and tags.count("h1") >= 1, page.name


def test_check_command_agrees(site) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "docket", "check", str(EXAMPLES)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "4 pages, 3 API endpoints, 0 warnings"
