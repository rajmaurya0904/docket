"""Render an API endpoint as an interactive "Try it" panel."""

from __future__ import annotations

import html
import json

from .api_parser import Endpoint
from .markdown import LinkRewriter, render_inline


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def endpoint_data(endpoint: Endpoint) -> dict:
    """The JSON blob the client script reads from ``data-endpoint``."""
    return {
        "method": endpoint.method,
        "path": endpoint.path,
        "params": [
            {
                "name": p.name,
                "location": p.location,
                "type": p.type,
                "required": p.required,
                "default": p.default,
            }
            for p in endpoint.params
        ],
        "headers": endpoint.headers,
        "body": endpoint.request_body,
        "responses": [{"status": r.status, "body": r.body} for r in endpoint.responses],
    }


def _code(body: str, lang: str) -> str:
    cls = f' class="language-{_esc(lang)}"' if lang else ""
    return f"<pre><code{cls}>{html.escape(body, quote=False)}</code></pre>"


def _param_table(endpoint: Endpoint) -> str:
    rows = []
    for p in endpoint.params:
        star = ' <span class="required" title="required">*</span>' if p.required else ""
        rows.append(
            f"<tr><td><code>{_esc(p.name)}</code>{star}</td><td>{_esc(p.location)}</td>"
            f"<td>{_esc(p.type)}</td><td>{_esc(p.description)}</td></tr>"
        )
    if not rows:
        return ""
    head = "<tr><th>Name</th><th>In</th><th>Type</th><th>Description</th></tr>"
    return f"<table>\n<thead>{head}</thead>\n<tbody>\n" + "\n".join(rows) + "\n</tbody>\n</table>"


def render_explorer(endpoint: Endpoint, rewrite: LinkRewriter | None = None) -> str:
    """Return the HTML for one endpoint panel.

    Panels built from a heading section only add the interactive part (the
    surrounding prose already documents the endpoint). Panels built from an
    ``api`` fence also render the summary, parameter table and examples, since
    the fence is the only documentation.
    """
    data = json.dumps(endpoint_data(endpoint), separators=(",", ":"))
    anchor = endpoint.anchor or "endpoint"
    method_class = f"m-{endpoint.method.lower()}"
    parts = [
        f'<section class="endpoint" id="{_esc(anchor)}-try" data-endpoint="{_esc(data)}">',
        f'<header><span class="method {method_class}">{_esc(endpoint.method)}</span> '
        f"<code>{_esc(endpoint.path)}</code></header>",
        '<div class="try"><p class="note">Enable JavaScript to try this endpoint.</p></div>',
    ]
    if endpoint.source == "fence":
        extra = []
        if endpoint.summary:
            extra.append(f"<p>{render_inline(endpoint.summary, rewrite)}</p>")
        extra.append(_param_table(endpoint))
        if endpoint.request_body:
            extra.append("<h4>Request body</h4>\n" + _code(endpoint.request_body, "json"))
        for response in endpoint.responses:
            title = f"<h4>Response {_esc(response.status)}</h4>\n"
            extra.append(title + _code(response.body, response.lang))
        parts.append('<div class="body">' + "\n".join(x for x in extra if x) + "</div>")
    parts.append("</section>")
    return "\n".join(parts)
