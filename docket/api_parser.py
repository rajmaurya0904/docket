"""Detect API endpoint definitions inside parsed Markdown.

Two notations are recognised, and both can appear in the same page.

1. A heading that starts with an HTTP method and a path::

       ## POST /users

       Create a user.

       ### Parameters

       | Name | In | Type | Required | Description |
       |------|----|------|----------|-------------|
       | dry_run | query | boolean | no | Validate only |

       ### Request Body

       ```json
       { "name": "string" }
       ```

       ### Response 201

       ```json
       { "id": 3 }
       ```

   The section under the heading (up to the next heading of the same or a higher
   level) is mined for a description, a parameter table, a request body and
   response examples, chosen by the words in their sub-headings.

2. A fenced block whose language is ``api``::

       ```api
       GET /users/{id}
       summary: Fetch one user
       param id path integer required: The user id
       param verbose query boolean: Include extra fields
       header Authorization: Bearer <token>
       response 200:
         { "id": 1, "name": "Alice" }
       ```

   Lines after ``body:`` or ``response <status>:`` that are indented by two or
   more spaces form the payload.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .markdown import (
    Block,
    CodeBlock,
    Heading,
    ListBlock,
    Paragraph,
    RawHtml,
    Table,
    plain_text,
    slugify,
)

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
LOCATIONS = ("path", "query", "header")

_SIGNATURE = re.compile(rf"^({'|'.join(METHODS)})\s+(/\S*)\s*$", re.I)
_PATH_PARAM = re.compile(r"\{([A-Za-z_][\w.-]*)\}")
_STATUS = re.compile(r"\b([1-5]\d\d)\b")
_TRUE = {"yes", "true", "required", "y", "x", "✓", "✔"}


@dataclass
class Param:
    name: str
    location: str = "query"
    type: str = "string"
    required: bool = False
    description: str = ""
    default: str = ""


@dataclass
class Response:
    status: str
    body: str
    lang: str = "json"


@dataclass
class Endpoint:
    method: str
    path: str
    summary: str = ""
    params: list[Param] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    request_body: str = ""
    responses: list[Response] = field(default_factory=list)
    anchor: str = ""
    source: str = "heading"
    warnings: list[str] = field(default_factory=list)

    @property
    def signature(self) -> str:
        return f"{self.method} {self.path}"

    def add_path_params(self) -> None:
        """Make sure every ``{name}`` in the path has a declared path parameter."""
        declared = {p.name for p in self.params if p.location == "path"}
        missing = [n for n in _PATH_PARAM.findall(self.path) if n not in declared]
        self.params[:0] = [Param(name=n, location="path", required=True) for n in missing]


def match_signature(text: str) -> tuple[str, str] | None:
    """Return ``(METHOD, path)`` if ``text`` is like ``GET /users/{id}``, else None."""
    m = _SIGNATURE.match(plain_text(text).strip())
    return (m.group(1).upper(), m.group(2)) if m else None


def _check_json(label: str, endpoint: Endpoint, body: str, lang: str) -> None:
    if lang.lower() != "json" or not body.strip():
        return
    try:
        json.loads(body)
    except json.JSONDecodeError as exc:
        endpoint.warnings.append(
            f"{endpoint.signature}: {label} is not valid JSON ({exc.msg} at line {exc.lineno})"
        )


def _truthy(cell: str) -> bool:
    return cell.strip().strip("*`").lower() in _TRUE


def _params_from_table(table: Table, endpoint: Endpoint) -> list[Param]:
    names = [plain_text(h).lower() for h in table.header]
    col = {
        key: names.index(alias)
        for key, aliases in {
            "name": ("name", "parameter", "param", "field"),
            "location": ("in", "location", "where"),
            "type": ("type",),
            "required": ("required", "req"),
            "description": ("description", "desc", "details"),
            "default": ("default",),
        }.items()
        for alias in aliases
        if alias in names
    }
    if "name" not in col:
        return []
    in_path = set(_PATH_PARAM.findall(endpoint.path))
    params = []
    for row in table.rows:

        def cell(key: str, row: list[str] = row) -> str:
            return plain_text(row[col[key]]) if key in col else ""

        name = cell("name")
        if not name:
            continue
        location = cell("location").lower() or ("path" if name in in_path else "query")
        if location not in LOCATIONS:
            endpoint.warnings.append(
                f"{endpoint.signature}: parameter '{name}' has unknown location '{location}'"
            )
            location = "query"
        params.append(
            Param(
                name=name,
                location=location,
                type=cell("type") or "string",
                required=_truthy(cell("required")) or location == "path",
                description=cell("description"),
                default=cell("default"),
            )
        )
    return params


def _status_of(text: str, info: str = "") -> str:
    m = _STATUS.search(text) or _STATUS.search(info)
    return m.group(1) if m else "200"


def parse_api_block(code: str) -> Endpoint:
    """Parse the body of an ``api`` fenced block. Raises ``ValueError`` on bad input."""
    lines = code.split("\n")
    first = next((i for i, ln in enumerate(lines) if ln.strip()), None)
    if first is None:
        raise ValueError("empty api block")
    sig = match_signature(lines[first])
    if sig is None:
        raise ValueError(f"api block must start with 'METHOD /path', got {lines[first].strip()!r}")
    endpoint = Endpoint(method=sig[0], path=sig[1], source="fence")

    payload_target: tuple[str, str] | None = None
    payload: list[str] = []

    def flush() -> None:
        nonlocal payload_target, payload
        if payload_target is None:
            return
        rows = "\n".join(payload).strip("\n").split("\n")
        indent = min((len(r) - len(r.lstrip()) for r in rows if r.strip()), default=0)
        text = "\n".join(r[indent:] for r in rows).strip("\n")
        kind, status = payload_target
        lang = "json" if text.lstrip()[:1] in "{[\"" or not text else "text"
        if kind == "body":
            endpoint.request_body = text
            _check_json("request body", endpoint, text, lang)
        else:
            endpoint.responses.append(Response(status=status, body=text, lang=lang))
            _check_json(f"response {status}", endpoint, text, lang)
        payload_target, payload = None, []

    for line in lines[first + 1 :]:
        if payload_target is not None and (line.startswith("  ") or not line.strip()):
            payload.append(line)
            continue
        flush()
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^body\s*:\s*$", stripped):
            payload_target = ("body", "")
        elif (m := re.match(r"^response\s+(\d{3})\s*:\s*$", stripped)) or (
            m := re.match(r"^response\s*:\s*$", stripped)
        ):
            payload_target = ("response", m.group(1) if m.groups() else "200")
        elif stripped.lower().startswith("summary:"):
            endpoint.summary = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("param "):
            endpoint.params.append(_parse_param_line(stripped, endpoint))
        elif stripped.lower().startswith("header "):
            name, _, value = stripped[7:].partition(":")
            if not name.strip():
                raise ValueError(f"header line has no name: {stripped!r}")
            endpoint.headers[name.strip()] = value.strip()
        else:
            raise ValueError(f"unrecognised line in api block: {stripped!r}")
    flush()
    endpoint.add_path_params()
    endpoint.anchor = slugify(endpoint.signature)
    return endpoint


def _parse_param_line(line: str, endpoint: Endpoint) -> Param:
    spec, _, description = line[6:].partition(":")
    words = spec.split()
    if len(words) < 2:
        raise ValueError(f"param needs a name and a location: {line!r}")
    name, location, rest = words[0], words[1].lower(), [w.lower() for w in words[2:]]
    if location not in LOCATIONS:
        raise ValueError(f"param location must be one of {', '.join(LOCATIONS)}: {line!r}")
    required = "required" in rest or location == "path"
    types = [w for w in rest if w != "required"]
    return Param(
        name=name,
        location=location,
        type=types[0] if types else "string",
        required=required,
        description=description.strip(),
    )


def _end_of_section(blocks: list[Block], start: int) -> int:
    level = blocks[start].level  # type: ignore[union-attr]
    for j in range(start + 1, len(blocks)):
        b = blocks[j]
        if isinstance(b, Heading) and b.level <= level:
            return j
    return len(blocks)


def _endpoint_from_section(heading: Heading, section: list[Block]) -> Endpoint:
    method, path = match_signature(heading.raw) or ("GET", "/")
    endpoint = Endpoint(method=method, path=path, anchor=heading.id or slugify(heading.text))
    sub = ""
    description: list[str] = []
    for block in section:
        if isinstance(block, Heading):
            sub = block.text.lower()
        elif isinstance(block, Paragraph) and not sub:
            description.append(block.text)
        elif isinstance(block, Table) and ("param" in sub or "quer" in sub or "header" in sub):
            endpoint.params.extend(_params_from_table(block, endpoint))
        elif isinstance(block, ListBlock):
            continue
        elif isinstance(block, CodeBlock):
            if "response" in sub:
                status = _status_of(sub, block.info)
                endpoint.responses.append(Response(status, block.code, block.lang))
                _check_json(f"response {status}", endpoint, block.code, block.lang)
            elif "request" in sub or "body" in sub or "payload" in sub:
                if not endpoint.request_body:
                    endpoint.request_body = block.code
                    _check_json("request body", endpoint, block.code, block.lang)
    endpoint.summary = " ".join(description).strip()
    endpoint.add_path_params()
    return endpoint


def extract(blocks: list[Block]) -> tuple[list[Endpoint], list[tuple[int, int, Endpoint]]]:
    """Find endpoints in ``blocks``.

    Returns ``(endpoints, placements)`` where each placement is
    ``(start, end, endpoint)``: for a heading section ``start`` is the heading
    index and ``end`` the index of the first block after the section; for an
    ``api`` fence ``end == start + 1`` and the fence itself is the extent.
    Raises ``ValueError`` for a malformed ``api`` block.
    """
    endpoints: list[Endpoint] = []
    placements: list[tuple[int, int, Endpoint]] = []
    for i, block in enumerate(blocks):
        if isinstance(block, Heading) and match_signature(block.raw):
            end = _end_of_section(blocks, i)
            endpoint = _endpoint_from_section(block, blocks[i + 1 : end])
            placements.append((i, end, endpoint))
            endpoints.append(endpoint)
        elif isinstance(block, CodeBlock) and block.lang.lower() == "api":
            try:
                endpoint = parse_api_block(block.code)
            except ValueError as exc:
                raise ValueError(f"invalid api block: {exc}") from exc
            placements.append((i, i + 1, endpoint))
            endpoints.append(endpoint)
    return endpoints, placements


def insert_explorers(
    blocks: list[Block], placements: list[tuple[int, int, Endpoint]], render_panel
) -> list[Block]:
    """Return ``blocks`` with an explorer panel added for each placement.

    ``render_panel(endpoint)`` must return an HTML string. Heading sections keep
    their original content and get the panel appended after it; ``api`` fences
    are replaced by the panel.
    """
    out: list[Block] = []
    after: dict[int, list[Endpoint]] = {}
    replace: dict[int, Endpoint] = {}
    for start, end, endpoint in placements:
        if end == start + 1 and isinstance(blocks[start], CodeBlock):
            replace[start] = endpoint
        else:
            after.setdefault(end, []).append(endpoint)
    for i, block in enumerate(blocks):
        for endpoint in after.get(i, []):
            out.append(RawHtml(render_panel(endpoint)))
        if i in replace:
            out.append(RawHtml(render_panel(replace[i])))
        else:
            out.append(block)
    for endpoint in after.get(len(blocks), []):
        out.append(RawHtml(render_panel(endpoint)))
    return out
