"""Static assets (stylesheet and client-side script) written into every built site."""

from __future__ import annotations

from pathlib import Path

CSS = """\
:root {
  --bg: #ffffff; --fg: #1f2328; --muted: #656d76; --line: #d8dee4; --panel: #f6f8fa;
  --accent: #0b5fff; --code-bg: #f3f4f6; --ok: #1a7f37; --bad: #cf222e;
  --sidebar: 17rem; --toc: 14rem;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f1216; --fg: #e6e8eb; --muted: #9aa4af; --line: #2a313a; --panel: #161b22;
    --accent: #6ea8ff; --code-bg: #1b2129; --ok: #3fb950; --bad: #ff7b72;
  }
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0; background: var(--bg); color: var(--fg); line-height: 1.6;
  font: 16px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
a { color: var(--accent); }
code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .9em; }
code { background: var(--code-bg); padding: .1em .35em; border-radius: 4px; }
pre { background: var(--code-bg); padding: .9rem 1rem; border-radius: 6px; overflow-x: auto; }
pre code { background: none; padding: 0; }
.layout { display: grid; grid-template-columns: var(--sidebar) minmax(0, 1fr) var(--toc); }
.sidebar {
  position: sticky; top: 0; height: 100vh; overflow-y: auto; padding: 1.25rem 1rem;
  border-right: 1px solid var(--line); background: var(--panel);
}
.sidebar .site-title { font-weight: 700; font-size: 1.1rem; text-decoration: none; color: var(--fg); }
.sidebar h2 {
  font-size: .75rem; text-transform: uppercase; letter-spacing: .06em; color: var(--muted);
  margin: 1.25rem 0 .35rem;
}
.sidebar ul { list-style: none; margin: 0; padding: 0; }
.sidebar li a {
  display: block; padding: .2rem .5rem; border-radius: 4px; text-decoration: none; color: var(--fg);
}
.sidebar li a:hover { background: var(--code-bg); }
.sidebar li a[aria-current="page"] { background: var(--accent); color: #fff; }
.search { width: 100%; margin-top: .9rem; padding: .4rem .6rem; border-radius: 6px;
  border: 1px solid var(--line); background: var(--bg); color: var(--fg); font: inherit; }
.search-results { margin-top: .5rem; }
.search-results small { color: var(--muted); display: block; }
main { padding: 2rem 2.5rem 4rem; max-width: 52rem; min-width: 0; }
main h1 { margin-top: 0; }
main h2 { margin-top: 2.2rem; padding-bottom: .3rem; border-bottom: 1px solid var(--line); }
.anchor { opacity: 0; margin-left: .3rem; text-decoration: none; font-weight: 400; }
h1:hover .anchor, h2:hover .anchor, h3:hover .anchor, h4:hover .anchor { opacity: .6; }
table { border-collapse: collapse; margin: 1rem 0; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--line); padding: .35rem .7rem; text-align: left; }
th { background: var(--panel); }
blockquote { margin: 1rem 0; padding: .1rem 1rem; border-left: 4px solid var(--line); color: var(--muted); }
img { max-width: 100%; }
.toc { position: sticky; top: 0; height: 100vh; overflow-y: auto; padding: 2rem 1rem; font-size: .85rem; }
.toc h2 { font-size: .75rem; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
.toc ul { list-style: none; padding: 0; margin: 0; }
.toc li a { display: block; padding: .15rem 0; color: var(--muted); text-decoration: none; }
.toc li a:hover { color: var(--fg); }
.toc li.l3 { padding-left: .8rem; }
.menu-toggle { display: none; }
.method {
  display: inline-block; min-width: 4.2rem; text-align: center; padding: .1rem .5rem;
  border-radius: 4px; font: 700 .8rem ui-monospace, Consolas, monospace; color: #fff; background: #57606a;
}
.m-get { background: #1a7f37; } .m-post { background: #0969da; } .m-put { background: #9a6700; }
.m-patch { background: #8250df; } .m-delete { background: #cf222e; }
.endpoint { border: 1px solid var(--line); border-radius: 8px; margin: 1.5rem 0; background: var(--panel); }
.endpoint > header { padding: .7rem 1rem; border-bottom: 1px solid var(--line); }
.endpoint > header code { background: none; font-size: 1rem; font-weight: 600; }
.endpoint .body { padding: .5rem 1rem 1rem; }
.endpoint label { display: block; font-size: .8rem; color: var(--muted); margin-top: .6rem; }
.endpoint input, .endpoint textarea {
  width: 100%; padding: .4rem .6rem; border: 1px solid var(--line); border-radius: 6px;
  background: var(--bg); color: var(--fg); font: .9rem ui-monospace, Consolas, monospace;
}
.endpoint textarea { min-height: 7rem; resize: vertical; }
.endpoint button.send {
  margin-top: .8rem; padding: .45rem 1.1rem; border: 0; border-radius: 6px; cursor: pointer;
  background: var(--accent); color: #fff; font: 600 .9rem system-ui, sans-serif;
}
.endpoint button.send[disabled] { opacity: .6; cursor: progress; }
.endpoint .curl { margin-top: .8rem; font-size: .8rem; white-space: pre-wrap; word-break: break-all; }
.endpoint .result { margin-top: .8rem; }
.endpoint .status { font: 600 .85rem ui-monospace, Consolas, monospace; }
.endpoint .status.ok { color: var(--ok); } .endpoint .status.bad { color: var(--bad); }
.endpoint .note { color: var(--muted); font-size: .85rem; }
.required { color: var(--bad); }
@media (max-width: 62rem) {
  .layout { grid-template-columns: var(--sidebar) minmax(0, 1fr); }
  .toc { display: none; }
}
@media (max-width: 44rem) {
  .layout { display: block; }
  .sidebar { position: fixed; z-index: 10; width: 80%; max-width: 20rem; transform: translateX(-100%);
    transition: transform .2s; }
  body.nav-open .sidebar { transform: none; box-shadow: 0 0 40px rgba(0,0,0,.4); }
  .menu-toggle { display: block; position: sticky; top: 0; z-index: 5; width: 100%; padding: .6rem 1rem;
    text-align: left; border: 0; border-bottom: 1px solid var(--line); background: var(--panel);
    color: var(--fg); font: inherit; cursor: pointer; }
  main { padding: 1.25rem 1rem 3rem; }
}
"""

JS = """\
/* docket client script: API explorer, sidebar search, mobile menu. No dependencies. */
(function (root) {
  "use strict";

  var BODY_METHODS = { POST: 1, PUT: 1, PATCH: 1 };

  function buildUrl(base, ep, values) {
    var path = ep.path.replace(/\\{([^}]+)\\}/g, function (_, name) {
      var v = values[name];
      if (v === undefined || v === "") throw new Error("Missing path parameter: " + name);
      return encodeURIComponent(v);
    });
    var query = [];
    ep.params.forEach(function (p) {
      var v = values[p.name];
      if (p.location !== "query") return;
      if (v === undefined || v === "") {
        if (p.required) throw new Error("Missing query parameter: " + p.name);
        return;
      }
      query.push(encodeURIComponent(p.name) + "=" + encodeURIComponent(v));
    });
    var url = base.replace(/\\/+$/, "") + path;
    return query.length ? url + "?" + query.join("&") : url;
  }

  function buildHeaders(ep, values, body) {
    var headers = {};
    Object.keys(ep.headers || {}).forEach(function (k) { headers[k] = ep.headers[k]; });
    ep.params.forEach(function (p) {
      var v = values[p.name];
      if (p.location === "header" && v) headers[p.name] = v;
    });
    var hasType = Object.keys(headers).some(function (k) { return k.toLowerCase() === "content-type"; });
    if (body && !hasType) headers["Content-Type"] = "application/json";
    return headers;
  }

  function shellQuote(s) {
    return "'" + String(s).replace(/'/g, "'\\\\''") + "'";
  }

  function buildCurl(url, method, headers, body) {
    var parts = ["curl -X " + method];
    Object.keys(headers).forEach(function (k) { parts.push("-H " + shellQuote(k + ": " + headers[k])); });
    if (body) parts.push("-d " + shellQuote(body));
    parts.push(shellQuote(url));
    return parts.join(" ");
  }

  function prettyBody(text, contentType) {
    if (/json/i.test(contentType || "") || /^\\s*[\\[{]/.test(text)) {
      try { return JSON.stringify(JSON.parse(text), null, 2); } catch (e) { /* not JSON */ }
    }
    return text;
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { node.appendChild(c); });
    return node;
  }

  function storage() {
    try { return root.localStorage; } catch (e) { return null; }
  }

  function initExplorer(section, getBase) {
    var ep = JSON.parse(section.getAttribute("data-endpoint"));
    var mount = section.querySelector(".try");
    if (!mount) return;
    mount.textContent = "";
    var inputs = {};
    var body = el("div", { "class": "body" });

    ep.params.forEach(function (p) {
      var input = el("input", { type: "text", autocomplete: "off", spellcheck: "false" });
      input.placeholder = p.type + (p.default ? " (default " + p.default + ")" : "");
      if (p.default) input.value = p.default;
      inputs[p.name] = input;
      var label = el("label", { text: p.name + " (" + p.location + ")" + (p.required ? " " : "") });
      if (p.required) label.appendChild(el("span", { "class": "required", text: "*" }));
      body.appendChild(label);
      body.appendChild(input);
    });

    var textarea = null;
    if (BODY_METHODS[ep.method] || ep.body) {
      textarea = el("textarea", { spellcheck: "false" });
      textarea.value = ep.body || "";
      body.appendChild(el("label", { text: "Request body" }));
      body.appendChild(textarea);
    }

    var curl = el("pre", { "class": "curl" });
    var button = el("button", { type: "button", "class": "send", text: "Send request" });
    var result = el("div", { "class": "result", "aria-live": "polite" });
    body.appendChild(button);
    body.appendChild(curl);
    body.appendChild(result);
    mount.appendChild(body);

    function values() {
      var out = {};
      Object.keys(inputs).forEach(function (k) { out[k] = inputs[k].value.trim(); });
      return out;
    }

    function current() {
      var v = values();
      var payload = textarea ? textarea.value.trim() : "";
      var base = getBase();
      var url = buildUrl(base || "{base-url}", ep, v);
      var headers = buildHeaders(ep, v, payload);
      return { url: url, headers: headers, payload: payload, base: base };
    }

    function refresh() {
      try {
        var c = current();
        curl.textContent = buildCurl(c.url, ep.method, c.headers, c.payload);
      } catch (e) {
        curl.textContent = e.message;
      }
    }

    function show(status, ok, text, note) {
      result.textContent = "";
      result.appendChild(el("div", { "class": "status " + (ok ? "ok" : "bad"), text: status }));
      if (note) result.appendChild(el("div", { "class": "note", text: note }));
      if (text) result.appendChild(el("pre", {}, [el("code", { text: text })]));
    }

    function send() {
      var c;
      try { c = current(); } catch (e) { show(e.message, false, ""); return; }
      if (!c.base) {
        var r = (ep.responses || [])[0];
        if (r) {
          show(r.status + " (documented example)", true, prettyBody(r.body, ""),
            "No base URL is set, so nothing was sent. Enter one above to call a live server.");
        } else {
          show("No base URL set", false, "", "Enter a base URL above to send a request.");
        }
        return;
      }
      if (c.base.indexOf("http") !== 0) { show("Base URL must start with http:// or https://", false, ""); return; }
      var init = { method: ep.method, headers: c.headers };
      if (c.payload && ep.method !== "GET" && ep.method !== "HEAD") init.body = c.payload;
      button.disabled = true;
      var started = Date.now();
      fetch(c.url, init).then(function (res) {
        return res.text().then(function (text) {
          show(res.status + " " + res.statusText, res.ok,
            prettyBody(text, res.headers.get("content-type")),
            (Date.now() - started) + " ms");
        });
      }).catch(function (err) {
        show("Request failed", false, "",
          err.message + ". The server may be down, or it may not allow cross-origin requests (CORS).");
      }).then(function () { button.disabled = false; });
    }

    button.addEventListener("click", send);
    mount.addEventListener("input", refresh);
    section.addEventListener("docket:base", refresh);
    refresh();
  }

  function initBaseUrl(explorers) {
    if (!explorers.length) return function () { return ""; };
    var meta = document.querySelector('meta[name="docket-base-url"]');
    var store = storage();
    var KEY = "docket.baseUrl";
    var initial = (store && store.getItem(KEY)) || (meta && meta.content) || "";
    var field = el("input", { type: "text", "class": "base-url", placeholder: "https://api.example.com" });
    field.value = initial;
    var bar = el("div", { "class": "endpoint" }, [
      el("div", { "class": "body" }, [el("label", { text: "API base URL (used by every Try it panel)" }), field])
    ]);
    bar.style.background = "transparent";
    explorers[0].parentNode.insertBefore(bar, explorers[0]);
    field.addEventListener("input", function () {
      if (store) { try { store.setItem(KEY, field.value.trim()); } catch (e) { /* ignore */ } }
      explorers.forEach(function (s) { s.dispatchEvent(new Event("docket:base")); });
    });
    return function () { return field.value.trim(); };
  }

  function initSearch() {
    var box = document.querySelector(".search");
    var out = document.querySelector(".search-results");
    var nav = document.querySelector(".sidebar nav");
    var index = root.DOCKET_INDEX;
    if (!box || !out || !index) return;
    var prefix = document.documentElement.getAttribute("data-root") || "";
    box.addEventListener("input", function () {
      var terms = box.value.toLowerCase().split(/\\s+/).filter(Boolean);
      out.textContent = "";
      if (!terms.length) { nav.hidden = false; return; }
      nav.hidden = true;
      var hits = index.filter(function (d) {
        var hay = (d.title + " " + d.text).toLowerCase();
        return terms.every(function (t) { return hay.indexOf(t) !== -1; });
      }).slice(0, 12);
      if (!hits.length) { out.appendChild(el("small", { text: "No matches" })); return; }
      hits.forEach(function (d) {
        out.appendChild(el("a", { href: prefix + d.url, text: d.title }));
        out.appendChild(el("small", { text: d.url }));
      });
    });
  }

  function init() {
    var toggle = document.querySelector(".menu-toggle");
    if (toggle) toggle.addEventListener("click", function () { document.body.classList.toggle("nav-open"); });
    var explorers = Array.prototype.slice.call(document.querySelectorAll(".endpoint[data-endpoint]"));
    var getBase = initBaseUrl(explorers);
    explorers.forEach(function (s) { initExplorer(s, getBase); });
    initSearch();
  }

  var api = { buildUrl: buildUrl, buildHeaders: buildHeaders, buildCurl: buildCurl, prettyBody: prettyBody };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else {
    root.Docket = api;
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
  }
})(typeof window !== "undefined" ? window : globalThis);
"""

ASSET_FILES = {"assets/docket.css": CSS, "assets/docket.js": JS}


def write_assets(out_dir: Path) -> list[Path]:
    """Write the stylesheet and script under ``out_dir/assets`` and return their paths."""
    written = []
    for relative, content in ASSET_FILES.items():
        target = Path(out_dir) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        written.append(target)
    return written
