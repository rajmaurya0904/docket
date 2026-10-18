"""Turn a directory of Markdown files into a static HTML site."""

from __future__ import annotations

import html
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import markdown as md
from .api_parser import Endpoint, extract, insert_explorers
from .assets import write_assets
from .discover import MARKDOWN_SUFFIXES, discover_markdown, is_hidden
from .explorer import render_explorer
from .frontmatter import parse_frontmatter
from .template import NavGroup, NavItem, TocEntry, render_page

MARKER = ".docket-site"
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


class BuildError(Exception):
    """A problem that stops the build (bad input, unreadable file, unsafe output path)."""


@dataclass
class Page:
    source: Path  # relative to the source directory
    url: str  # relative to the site root, posix style
    title: str
    description: str
    order: int
    blocks: list[md.Block]
    endpoints: list[Endpoint] = field(default_factory=list)
    has_h1: bool = False
    generated: bool = False

    @property
    def group(self) -> str:
        parent = PurePosixPath(self.url).parent.as_posix()
        return "" if parent == "." else parent


@dataclass
class BuildResult:
    pages: list[Page]
    output: Path | None
    warnings: list[str] = field(default_factory=list)
    files_written: int = 0

    @property
    def endpoints(self) -> int:
        return sum(len(p.endpoints) for p in self.pages)


def prettify(name: str) -> str:
    """``getting-started`` -> ``Getting Started``."""
    words = re.split(r"[-_\s]+", name.strip())
    return " ".join(w[:1].upper() + w[1:] for w in words if w) or name


def url_for(relative: Path) -> str:
    """Output URL for a source file: ``a/b.md`` -> ``a/b.html``."""
    return relative.with_suffix(".html").as_posix()


def relative_url(target: str, current: str) -> str:
    """Link from the page at ``current`` to ``target`` (both site-relative, posix)."""
    start = PurePosixPath(current).parent.parts
    dest = PurePosixPath(target).parts
    common = 0
    while common < min(len(start), len(dest) - 1) and start[common] == dest[common]:
        common += 1
    parts = [".."] * (len(start) - common) + list(dest[common:])
    return "/".join(parts) or "."


def root_prefix(url: str) -> str:
    return "../" * (len(PurePosixPath(url).parts) - 1)


def _normalize(path: str) -> str | None:
    """Collapse ``.`` and ``..``; None if the path climbs above the root."""
    out: list[str] = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not out:
                return None
            out.pop()
        else:
            out.append(part)
    return "/".join(out)


def _check_output(source: Path, output: Path) -> None:
    src, out = source.resolve(), output.resolve()
    if out == src or src in out.parents:
        relative = out.relative_to(src) if out != src else Path(".")
        if out == src or not is_hidden(relative):
            raise BuildError(
                f"output directory {output} is inside the source directory; "
                "choose a location outside it, or one starting with '_' or '.'"
            )
    if out in src.parents:
        raise BuildError(f"output directory {output} would contain the source directory")
    if out.exists() and not out.is_dir():
        raise BuildError(f"output path exists and is not a directory: {output}")


def _clean(output: Path) -> None:
    if not output.exists():
        return
    if any(output.iterdir()) and not (output / MARKER).exists():
        raise BuildError(
            f"refusing to clean {output}: it is not empty and was not created by docket"
        )
    shutil.rmtree(output)


def _blocks_text(blocks: list[md.Block]) -> str:
    chunks: list[str] = []
    for block in blocks:
        if isinstance(block, md.Heading):
            chunks.append(block.text)
        elif isinstance(block, md.Paragraph):
            chunks.append(md.plain_text(block.text))
        elif isinstance(block, md.Quote):
            chunks.append(_blocks_text(block.blocks))
        elif isinstance(block, md.ListBlock):
            chunks.extend(_blocks_text(item.blocks) for item in block.items)
        elif isinstance(block, md.Table):
            chunks.extend(md.plain_text(c) for c in block.header)
            chunks.extend(md.plain_text(c) for row in block.rows for c in row)
    return " ".join(c for c in chunks if c)


def load_page(source: Path, relative: Path, warnings: list[str]) -> Page:
    """Read and parse one Markdown file into a Page."""
    path = source / relative
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise BuildError(f"{relative.as_posix()}: not valid UTF-8 ({exc.reason})") from exc
    except OSError as exc:
        raise BuildError(f"{relative.as_posix()}: cannot read file ({exc.strerror})") from exc

    meta, body = parse_frontmatter(text)
    blocks = md.parse(body)
    h1 = next((h for h in md.headings_of(blocks) if h.level == 1), None)
    title = meta.get("title") or (h1.text if h1 else "") or prettify(relative.stem)

    order = 1000
    if "order" in meta:
        try:
            order = int(meta["order"])
        except ValueError:
            warnings.append(
                f"{relative.as_posix()}: 'order' must be an integer, got {meta['order']!r}"
            )

    page = Page(
        source=relative,
        url=url_for(relative),
        title=title,
        description=meta.get("description", ""),
        order=order,
        blocks=blocks,
        has_h1=h1 is not None,
    )
    try:
        endpoints, placements = extract(blocks)
    except ValueError as exc:
        raise BuildError(f"{relative.as_posix()}: {exc}") from exc
    page.endpoints = endpoints
    for endpoint in endpoints:
        warnings.extend(f"{relative.as_posix()}: {w}" for w in endpoint.warnings)
    page.blocks = insert_explorers(blocks, placements, lambda e: render_explorer(e))
    return page


def _index_page(pages: list[Page], site_title: str) -> Page:
    lines = [f"# {site_title}", ""]
    groups: dict[str, list[Page]] = {}
    for page in pages:
        groups.setdefault(page.group, []).append(page)
    for group in sorted(groups, key=lambda g: (g != "", g)):
        if group:
            lines += [f"## {prettify(group.replace('/', ' / '))}", ""]
        for page in sorted(groups[group], key=lambda p: (p.order, p.title.lower())):
            lines.append(f"- [{page.title}]({page.url})")
        lines.append("")
    blocks = md.parse("\n".join(lines))
    return Page(
        source=Path("index.md"),
        url="index.html",
        title=site_title,
        description="",
        order=-1,
        blocks=blocks,
        has_h1=True,
        generated=True,
    )


def build_nav(pages: list[Page]) -> list[NavGroup]:
    groups: dict[str, list[Page]] = {}
    for page in pages:
        groups.setdefault(page.group, []).append(page)
    nav = []
    for group in sorted(groups, key=lambda g: (g != "", g.lower())):
        title = prettify(group.replace("/", " / ")) if group else ""
        ordered = sorted(
            groups[group], key=lambda p: (p.url != "index.html", p.order, p.title.lower())
        )
        nav.append(NavGroup(title, [NavItem(p.title, p.url) for p in ordered]))
    return nav


class _LinkResolver:
    def __init__(self, pages: list[Page], source: Path, warnings: list[str]) -> None:
        self.by_source = {p.source.as_posix(): p for p in pages}
        self.source = source
        self.warnings = warnings

    def make(self, page: Page):
        def rewrite(url: str) -> str:
            return self.resolve(page, url)

        return rewrite

    def resolve(self, page: Page, url: str) -> str:
        if not url or url.startswith(("#", "//")) or _SCHEME.match(url):
            return url
        path, hash_mark, fragment = url.partition("#")
        path, _, query = path.partition("?")
        here = PurePosixPath(page.source.as_posix()).parent.as_posix()
        base = "" if path.startswith("/") else here
        joined = path if path.startswith("/") else f"{base}/{path}"
        norm = _normalize(joined)
        where = page.source.as_posix()
        if norm is None:
            self.warnings.append(f"{where}: link '{url}' points outside the documentation root")
            return url
        target = self._find_page(norm, path)
        if target is not None:
            if hash_mark and fragment and not self._has_anchor(target, fragment):
                self.warnings.append(
                    f"{where}: link '{url}' has no heading '#{fragment}' "
                    f"in {target.source.as_posix()}"
                )
            href = relative_url(target.url, page.url)
            return href + (f"?{query}" if query else "") + (f"#{fragment}" if hash_mark else "")
        local = self.source / norm
        if norm and local.is_file() and not is_hidden(Path(norm)):
            return relative_url(norm, page.url) + (f"?{query}" if query else "") + (
                f"#{fragment}" if hash_mark else ""
            )
        self.warnings.append(f"{where}: broken link '{url}' (no such page or file)")
        return url

    def _find_page(self, norm: str, original: str) -> Page | None:
        suffix = PurePosixPath(norm).suffix.lower()
        if suffix in MARKDOWN_SUFFIXES:
            return self.by_source.get(norm)
        if suffix == ".html":
            for page in self.by_source.values():
                if page.url == norm:
                    return page
            return None
        if suffix:
            return None
        stem = norm
        candidates = (
            [f"{stem}.md", f"{stem}.markdown", f"{stem}/index.md"] if stem else ["index.md"]
        )
        for cand in candidates:
            if cand in self.by_source:
                return self.by_source[cand]
        return None

    def _has_anchor(self, page: Page, fragment: str) -> bool:
        ids = {b.id for b in page.blocks if isinstance(b, md.Heading)}
        ids |= {e.anchor + "-try" for e in page.endpoints}
        return fragment in ids


def build(
    source: Path | str,
    output: Path | str | None,
    *,
    site_title: str = "Documentation",
    base_url: str = "",
    clean: bool = False,
    search: bool = True,
) -> BuildResult:
    """Build the site from ``source`` into ``output``.

    With ``output=None`` nothing is written: the sources are parsed and every link
    and example is checked, which is what ``docket check`` uses. Raises
    ``BuildError`` for problems that make a correct site impossible; softer
    issues (a broken link, invalid example JSON) are returned in ``warnings``.
    """
    src = Path(source)
    if not src.exists():
        raise BuildError(f"source directory not found: {src}")
    if not src.is_dir():
        raise BuildError(f"source is not a directory: {src}")
    out = Path(output) if output is not None else None
    if out is not None:
        _check_output(src, out)

    relatives = discover_markdown(src)
    if not relatives:
        raise BuildError(f"no Markdown files found in {src}")

    warnings: list[str] = []
    pages: list[Page] = []
    seen: dict[str, Path] = {}
    for relative in relatives:
        page = load_page(src, relative, warnings)
        if page.url in seen:
            raise BuildError(
                f"{relative.as_posix()} and {seen[page.url].as_posix()} would both write {page.url}"
            )
        seen[page.url] = relative
        pages.append(page)

    if "index.html" not in seen:
        pages.append(_index_page(pages, site_title))

    nav = build_nav(pages)
    resolver = _LinkResolver(pages, src, warnings)
    rendered: list[tuple[Page, str, list[TocEntry]]] = []
    for page in pages:
        body = md.render_blocks(page.blocks, resolver.make(page))
        if not page.has_h1:
            body = f"<h1>{html.escape(page.title, quote=False)}</h1>\n{body}"
        toc = [TocEntry(h.level, h.text, h.id) for h in md.headings_of(page.blocks)]
        rendered.append((page, body, toc))

    result = BuildResult(pages=pages, output=out, warnings=warnings)
    if out is None:
        return result

    if clean:
        _clean(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / MARKER).write_text("generated by docket\n", encoding="utf-8")

    for name in sorted(_static_files(src)):
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / name, dest)
        result.files_written += 1

    index_entries = []
    for page, body, toc in rendered:
        html_doc = render_page(
            site_title=site_title,
            page_title=page.title,
            body_html=body,
            nav=nav,
            current=page.url,
            root=root_prefix(page.url),
            toc=toc,
            description=page.description,
            base_url=base_url,
            search_index=search,
        )
        target = out / page.url
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html_doc, encoding="utf-8", newline="\n")
        result.files_written += 1
        index_entries.append(
            {"title": page.title, "url": page.url, "text": _blocks_text(page.blocks)[:2000]}
        )

    result.files_written += len(write_assets(out))
    if search:
        payload = json.dumps(index_entries, ensure_ascii=True).replace("</", "<\\/")
        script = out / "assets" / "search-index.js"
        script.write_text(f"window.DOCKET_INDEX = {payload};\n", encoding="utf-8", newline="\n")
        result.files_written += 1

    return result


def _static_files(src: Path) -> list[str]:
    """Non-Markdown files to copy as-is (images, downloads), skipping hidden paths."""
    found = []
    for path in src.rglob("*"):
        if not path.is_file() or path.suffix.lower() in MARKDOWN_SUFFIXES:
            continue
        relative = path.relative_to(src)
        if is_hidden(relative):
            continue
        found.append(relative.as_posix())
    return found
