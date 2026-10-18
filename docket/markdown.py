"""A small Markdown compiler with no dependencies.

It covers the parts of Markdown that documentation actually uses: ATX and setext
headings, paragraphs, fenced and indented code, block quotes, nested ordered,
unordered and task lists, tables with alignment, horizontal rules, raw HTML
blocks, and the inline forms ``code``, ``**bold**``, ``*italic*``, ``~~strike~~``,
links, images and autolinks.

Parsing and rendering are separate steps so other modules (the API explorer)
can inspect and rewrite the block list between them.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from dataclasses import dataclass, field

LinkRewriter = Callable[[str], str]


@dataclass
class Heading:
    level: int
    raw: str
    id: str = ""

    @property
    def text(self) -> str:
        return plain_text(self.raw)


@dataclass
class Paragraph:
    text: str


@dataclass
class CodeBlock:
    code: str
    lang: str = ""
    info: str = ""


@dataclass
class Quote:
    blocks: list[Block]


@dataclass
class ListItem:
    blocks: list[Block]
    checked: bool | None = None


@dataclass
class ListBlock:
    ordered: bool
    items: list[ListItem]
    start: int = 1
    loose: bool = False


@dataclass
class Table:
    header: list[str]
    aligns: list[str]
    rows: list[list[str]]


@dataclass
class Rule:
    pass


@dataclass
class RawHtml:
    html: str


Block = Heading | Paragraph | CodeBlock | Quote | ListBlock | Table | Rule | RawHtml


@dataclass
class Rendered:
    html: str
    headings: list[Heading] = field(default_factory=list)


# --------------------------------------------------------------------------- inline

_PLACEHOLDER = re.compile("\x00(\\d+)\x00")
_CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.S)
_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|~<>])")
_AUTOLINK = re.compile(r"<((?:https?|mailto):[^\s<>]+)>")
_IMAGE = re.compile(r'!\[([^\]]*)\]\(\s*([^)\s]+)(?:\s+"([^"]*)")?\s*\)')
_LINK = re.compile(r'\[([^\]]+)\]\(\s*([^)\s]+)(?:\s+"([^"]*)")?\s*\)')
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*|(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)", re.S)
_ITALIC = re.compile(
    r"\*(?=[^\s*])(.+?)(?<=[^\s*])\*|(?<!\w)_(?=[^\s_])(.+?)(?<=[^\s_])_(?!\w)", re.S
)
_STRIKE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~", re.S)


def _attr(value: str) -> str:
    return html.escape(value, quote=True)


def _emphasis(text: str) -> str:
    text = _BOLD.sub(lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>", text)
    text = _ITALIC.sub(lambda m: f"<em>{m.group(1) or m.group(2)}</em>", text)
    return _STRIKE.sub(lambda m: f"<del>{m.group(1)}</del>", text)


def render_inline(text: str, rewrite: LinkRewriter | None = None) -> str:
    """Render inline Markdown ``text`` to HTML. Everything else is HTML-escaped."""
    stash: list[str] = []

    def keep(fragment: str) -> str:
        stash.append(fragment)
        return f"\x00{len(stash) - 1}\x00"

    def href(url: str) -> str:
        return _attr(rewrite(url) if rewrite else url)

    text = text.replace("\x00", "")
    text = _CODE_SPAN.sub(
        lambda m: keep(f"<code>{html.escape(m.group(2).strip(), quote=False)}</code>"), text
    )
    text = _ESCAPE.sub(lambda m: keep(html.escape(m.group(1), quote=False)), text)
    text = _AUTOLINK.sub(
        lambda m: keep(f'<a href="{_attr(m.group(1))}">{html.escape(m.group(1), quote=False)}</a>'),
        text,
    )
    text = html.escape(text, quote=False)

    def image(m: re.Match[str]) -> str:
        title = f' title="{_attr(m.group(3))}"' if m.group(3) else ""
        return keep(f'<img src="{href(m.group(2))}" alt="{_attr(m.group(1))}"{title}>')

    def link(m: re.Match[str]) -> str:
        title = f' title="{_attr(m.group(3))}"' if m.group(3) else ""
        inner = _PLACEHOLDER.sub(lambda p: stash[int(p.group(1))], _emphasis(m.group(1)))
        return keep(f'<a href="{href(m.group(2))}"{title}>{inner}</a>')

    text = _IMAGE.sub(image, text)
    text = _LINK.sub(link, text)
    text = _emphasis(text)
    text = re.sub(r" {2,}\n", "<br>\n", text)
    while _PLACEHOLDER.search(text):
        text = _PLACEHOLDER.sub(lambda p: stash[int(p.group(1))], text)
    return text


def plain_text(inline: str) -> str:
    """Strip inline Markdown from ``inline`` leaving the readable text."""
    text = _IMAGE.sub(lambda m: m.group(1), inline)
    text = _LINK.sub(lambda m: m.group(1), text)
    text = _CODE_SPAN.sub(lambda m: m.group(2), text)
    text = _ESCAPE.sub(lambda m: m.group(1), text)
    return re.sub(r"[*_~`]", "", text).strip()


def slugify(text: str) -> str:
    """Reduce ``text`` to a URL-safe anchor, e.g. ``GET /users`` -> ``get-users``."""
    slug = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    return re.sub(r"[\s_-]+", "-", slug).strip("-")


# ---------------------------------------------------------------------------- blocks

_FENCE = re.compile(r"^( {0,3})(`{3,}|~{3,})\s*([^\s`]*)\s*(.*)$")
_ATX = re.compile(r"^ {0,3}(#{1,6})(?:\s+(.*?))?(?:\s+#+)?\s*$")
_RULE = re.compile(r"^ {0,3}([-*_])(?:\s*\1){2,}\s*$")
_QUOTE = re.compile(r"^ {0,3}>")
_ITEM = re.compile(r"^( *)([-*+]|\d{1,9}[.)])( +|$)(.*)$")
_SETEXT = re.compile(r"^ {0,3}(=+|-+)\s*$")
_TABLE_DELIM = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
_HTML_START = re.compile(r"^ {0,3}(<!--|</?[A-Za-z][\w-]*(\s|/?>|$))")
_TASK = re.compile(r"^\[([ xX])\]\s+")


def _is_blank(line: str) -> bool:
    return not line.strip()


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    cells = re.split(r"(?<!\\)\|", line)
    return [c.strip().replace("\\|", "|") for c in cells]


def _align(cell: str) -> str:
    cell = cell.strip()
    if cell.startswith(":") and cell.endswith(":"):
        return "center"
    if cell.endswith(":"):
        return "right"
    if cell.startswith(":"):
        return "left"
    return ""


def _starts_block(line: str) -> bool:
    """True if ``line`` would interrupt a paragraph."""
    if _FENCE.match(line) or _QUOTE.match(line) or _ATX.match(line):
        return True
    item = _ITEM.match(line)
    if item and item.group(4).strip():
        marker = item.group(2)
        return not marker[0].isdigit() or marker.rstrip(".)") == "1"
    return bool(_RULE.match(line))


def _parse_list(lines: list[str], i: int) -> tuple[ListBlock, int]:
    first = _ITEM.match(lines[i])
    assert first is not None
    base = len(first.group(1))
    ordered = first.group(2)[0].isdigit()
    start = int(first.group(2).rstrip(".)")) if ordered else 1
    items_lines: list[list[str]] = []
    loose = False
    current: list[str] | None = None
    offset = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if _is_blank(line):
            j = i
            while j < n and _is_blank(lines[j]):
                j += 1
            if j >= n:
                break
            nxt = lines[j]
            m = _ITEM.match(nxt)
            indent = len(nxt) - len(nxt.lstrip(" "))
            if m and len(m.group(1)) == base and (m.group(2)[0].isdigit() == ordered):
                loose = True
                i = j
                continue
            if indent > base and current is not None:
                current.extend([""] * (j - i))
                i = j
                continue
            break
        m = _ITEM.match(line)
        indent = len(line) - len(line.lstrip(" "))
        if m and len(m.group(1)) <= base and not _RULE.match(line):
            if len(m.group(1)) < base or m.group(2)[0].isdigit() != ordered:
                break
            spaces = len(m.group(3))
            offset = len(m.group(1)) + len(m.group(2)) + (spaces if 1 <= spaces <= 4 else 1)
            current = [m.group(4)]
            items_lines.append(current)
            i += 1
            continue
        if current is None:
            break
        if indent > base or not _starts_block(line):
            if _RULE.match(line) and indent <= base:
                break
            current.append(line[min(indent, offset) :] if indent else line)
            i += 1
            continue
        break
    items = []
    for body in items_lines:
        checked: bool | None = None
        task = _TASK.match(body[0])
        if task:
            checked = task.group(1).lower() == "x"
            body[0] = body[0][task.end() :]
        items.append(ListItem(blocks=_parse_blocks(body, None), checked=checked))
    return ListBlock(ordered=ordered, items=items, start=start, loose=loose), i


def _parse_blocks(lines: list[str], counter: dict[str, int] | None) -> list[Block]:
    blocks: list[Block] = []
    i, n = 0, len(lines)

    def add_heading(level: int, raw: str) -> None:
        h = Heading(level=level, raw=raw)
        if counter is not None:
            base = slugify(h.text) or "section"
            seen = counter.get(base, 0)
            counter[base] = seen + 1
            h.id = base if seen == 0 else f"{base}-{seen}"
        blocks.append(h)

    while i < n:
        line = lines[i]
        if _is_blank(line):
            i += 1
            continue

        fence = _FENCE.match(line)
        if fence:
            indent, marker, lang, rest = fence.groups()
            body: list[str] = []
            i += 1
            while i < n:
                close = _FENCE.match(lines[i])
                if (
                    close
                    and close.group(2)[0] == marker[0]
                    and len(close.group(2)) >= len(marker)
                    and not close.group(3)
                    and not close.group(4)
                ):
                    i += 1
                    break
                text = lines[i]
                strip = min(len(indent), len(text) - len(text.lstrip(" ")))
                body.append(text[strip:])
                i += 1
            info = (lang + " " + rest).strip()
            blocks.append(CodeBlock(code="\n".join(body), lang=lang, info=info))
            continue

        atx = _ATX.match(line)
        if atx:
            add_heading(len(atx.group(1)), atx.group(2) or "")
            i += 1
            continue

        if _RULE.match(line):
            blocks.append(Rule())
            i += 1
            continue

        if _QUOTE.match(line):
            inner: list[str] = []
            while i < n and not _is_blank(lines[i]):
                if _QUOTE.match(lines[i]):
                    inner.append(re.sub(r"^ {0,3}> ?", "", lines[i]))
                elif _starts_block(lines[i]):
                    break
                else:
                    inner.append(lines[i])
                i += 1
            blocks.append(Quote(blocks=_parse_blocks(inner, None)))
            continue

        if _ITEM.match(line):
            lst, i = _parse_list(lines, i)
            blocks.append(lst)
            continue

        if line.startswith("    "):
            code: list[str] = []
            while i < n and (lines[i].startswith("    ") or _is_blank(lines[i])):
                code.append(lines[i][4:])
                i += 1
            while code and not code[-1].strip():
                code.pop()
            blocks.append(CodeBlock(code="\n".join(code)))
            continue

        if "|" in line and i + 1 < n and _TABLE_DELIM.match(lines[i + 1]) and "-" in lines[i + 1]:
            header = _split_row(line)
            delim = _split_row(lines[i + 1])
            if len(header) == len(delim):
                rows = []
                i += 2
                while i < n and not _is_blank(lines[i]) and "|" in lines[i]:
                    row = _split_row(lines[i])
                    rows.append((row + [""] * len(header))[: len(header)])
                    i += 1
                blocks.append(Table(header=header, aligns=[_align(c) for c in delim], rows=rows))
                continue

        if _HTML_START.match(line):
            raw: list[str] = []
            while i < n and not _is_blank(lines[i]):
                raw.append(lines[i])
                i += 1
            blocks.append(RawHtml("\n".join(raw)))
            continue

        para = [line.lstrip()]
        i += 1
        setext_level = 0
        while i < n and not _is_blank(lines[i]):
            setext = _SETEXT.match(lines[i])
            if setext:
                setext_level = 1 if setext.group(1)[0] == "=" else 2
                i += 1
                break
            if _starts_block(lines[i]):
                break
            para.append(lines[i].rstrip() if lines[i].endswith("  ") else lines[i].strip())
            i += 1
        if setext_level:
            add_heading(setext_level, " ".join(p.strip() for p in para))
        else:
            blocks.append(Paragraph("\n".join(para)))
    return blocks


def parse(text: str) -> list[Block]:
    """Parse Markdown ``text`` into a list of blocks. Heading ids are unique per call."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").expandtabs(4)
    return _parse_blocks(text.split("\n"), {})


def headings_of(blocks: list[Block]) -> list[Heading]:
    """Return the top-level headings of ``blocks`` in document order."""
    return [b for b in blocks if isinstance(b, Heading)]


# -------------------------------------------------------------------------- rendering


def render_blocks(blocks: list[Block], rewrite: LinkRewriter | None = None) -> str:
    """Render parsed ``blocks`` to an HTML string."""
    out = [_render_block(b, rewrite, False) for b in blocks]
    return "\n".join(part for part in out if part)


def _render_block(block: Block, rewrite: LinkRewriter | None, tight: bool) -> str:
    def inline(s: str) -> str:
        return render_inline(s, rewrite)

    if isinstance(block, Heading):
        ident = f' id="{_attr(block.id)}"' if block.id else ""
        anchor = ""
        if block.id:
            anchor = (
                f' <a class="anchor" href="#{_attr(block.id)}" aria-label="Link to section">#</a>'
            )
        return f"<h{block.level}{ident}>{inline(block.raw)}{anchor}</h{block.level}>"
    if isinstance(block, Paragraph):
        body = inline(block.text)
        return body if tight else f"<p>{body}</p>"
    if isinstance(block, CodeBlock):
        cls = f' class="language-{_attr(block.lang)}"' if block.lang else ""
        return f"<pre><code{cls}>{html.escape(block.code, quote=False)}</code></pre>"
    if isinstance(block, Rule):
        return "<hr>"
    if isinstance(block, RawHtml):
        return block.html
    if isinstance(block, Quote):
        return f"<blockquote>\n{render_blocks(block.blocks, rewrite)}\n</blockquote>"
    if isinstance(block, ListBlock):
        tag = "ol" if block.ordered else "ul"
        attr = f' start="{block.start}"' if block.ordered and block.start != 1 else ""
        lines = [f"<{tag}{attr}>"]
        for item in block.items:
            parts = [_render_block(b, rewrite, not block.loose) for b in item.blocks]
            body = "\n".join(p for p in parts if p)
            if item.checked is not None:
                mark = " checked" if item.checked else ""
                body = f'<input type="checkbox" disabled{mark}> {body}'
            lines.append(f"<li>{body}</li>")
        lines.append(f"</{tag}>")
        return "\n".join(lines)
    if isinstance(block, Table):

        def cell(tag: str, text: str, align: str) -> str:
            style = f' style="text-align:{align}"' if align else ""
            return f"<{tag}{style}>{inline(text)}</{tag}>"

        head = "".join(cell("th", c, a) for c, a in zip(block.header, block.aligns, strict=True))
        rows = "\n".join(
            "<tr>"
            + "".join(cell("td", c, a) for c, a in zip(r, block.aligns, strict=True))
            + "</tr>"
            for r in block.rows
        )
        return f"<table>\n<thead><tr>{head}</tr></thead>\n<tbody>\n{rows}\n</tbody>\n</table>"
    raise TypeError(f"unknown block: {block!r}")


def render(text: str, rewrite: LinkRewriter | None = None) -> Rendered:
    """Compile Markdown ``text`` to HTML, returning the HTML and its headings."""
    blocks = parse(text)
    return Rendered(html=render_blocks(blocks, rewrite), headings=headings_of(blocks))
