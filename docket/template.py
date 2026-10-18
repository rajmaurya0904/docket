"""The HTML page shell: sidebar navigation, content column, on-page table of contents."""

from __future__ import annotations

import html
from dataclasses import dataclass, field


@dataclass
class NavItem:
    title: str
    url: str  # relative to the site root, e.g. "api/users.html"


@dataclass
class NavGroup:
    title: str  # empty for the ungrouped top-level pages
    items: list[NavItem] = field(default_factory=list)


@dataclass
class TocEntry:
    level: int
    text: str
    id: str


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def render_nav(groups: list[NavGroup], current: str, root: str) -> str:
    """Render the sidebar links. ``current`` is the active page URL (site-relative)."""
    parts = []
    for group in groups:
        if group.title:
            parts.append(f"<h2>{_esc(group.title)}</h2>")
        items = []
        for item in group.items:
            aria = ' aria-current="page"' if item.url == current else ""
            items.append(f'<li><a href="{_esc(root + item.url)}"{aria}>{_esc(item.title)}</a></li>')
        parts.append("<ul>\n" + "\n".join(items) + "\n</ul>")
    return "\n".join(parts)


def render_toc(entries: list[TocEntry]) -> str:
    """Render the "On this page" list from level 2 and 3 headings."""
    shown = [e for e in entries if e.level in (2, 3) and e.id]
    if len(shown) < 2:
        return ""
    items = "\n".join(
        f'<li class="l{e.level}"><a href="#{_esc(e.id)}">{_esc(e.text)}</a></li>' for e in shown
    )
    return f'<aside class="toc"><h2>On this page</h2>\n<ul>\n{items}\n</ul></aside>'


def render_page(
    *,
    site_title: str,
    page_title: str,
    body_html: str,
    nav: list[NavGroup],
    current: str,
    root: str,
    toc: list[TocEntry] | None = None,
    description: str = "",
    base_url: str = "",
    search_index: bool = False,
) -> str:
    """Return a complete HTML document.

    ``root`` is the relative path from this page back to the site root (``""``,
    ``"../"``, ...), so the generated site works from any directory and from
    ``file://``. Titles and descriptions are HTML-escaped; ``body_html`` is
    trusted, already-rendered markup.
    """
    full_title = site_title if page_title == site_title else f"{page_title} - {site_title}"
    meta_desc = f'<meta name="description" content="{_esc(description)}">\n' if description else ""
    meta_base = f'<meta name="docket-base-url" content="{_esc(base_url)}">\n' if base_url else ""
    index_script = f'<script src="{root}assets/search-index.js"></script>\n' if search_index else ""
    search = (
        '<input class="search" type="search" placeholder="Search docs" aria-label="Search docs">\n'
        '<div class="search-results"></div>\n'
        if search_index
        else ""
    )
    toc_html = render_toc(toc or [])
    return f"""<!doctype html>
<html lang="en" data-root="{_esc(root)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(full_title)}</title>
{meta_desc}{meta_base}<link rel="stylesheet" href="{root}assets/docket.css">
</head>
<body>
<button class="menu-toggle" type="button" aria-label="Toggle navigation">Menu</button>
<div class="layout">
<div class="sidebar">
<a class="site-title" href="{root}index.html">{_esc(site_title)}</a>
{search}<nav aria-label="Pages">
{render_nav(nav, current, root)}
</nav>
</div>
<main>
{body_html}
</main>
{toc_html}
</div>
{index_script}<script src="{root}assets/docket.js"></script>
</body>
</html>
"""
