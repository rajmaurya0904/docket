# docket

**A zero-dependency static docs generator for Python 3.11+: point it at a folder of Markdown and get a navigable site where every `GET /users`-style section becomes a "Try it" panel.**

Most docs toolchains want a Node install, a plugin zoo and a config file before they will render a single page, and API pages still end up as a screenshot of Postman. Docket is one pure-Python package with no runtime dependencies. If you already wrote `## GET /users/{id}` in a Markdown file, that heading is all it needs to build a form that calls your API from the browser.

```console
$ docket build examples -o site -t "Docket example"
  api/health.md                -> api/health.html
  api/users.md                 -> api/users.html
  guide/introduction.md        -> guide/introduction.html
  index.md                     -> index.html
4 pages, 3 API endpoints, 0 warnings
wrote 7 files to site

$ docket check examples      # after adding two bad links to index.md
warning: index.md: broken link 'roadmap.md' (no such page or file)
warning: index.md: link 'guide/introduction.md#nope' has no heading '#nope' in guide/introduction.md
4 pages, 3 API endpoints, 2 warnings

$ echo $?
1

$ docket build nowhere
error: source directory not found: nowhere
```

Opening `site/api/users.html` in a browser shows the prose you wrote plus, under each endpoint, a form with the path and query parameters, an editable request body, a live `curl` command and a Send button. With no API base URL set, Send shows the response you documented and says so. With one set, it makes the real request and prints the status, timing and pretty-printed body.

## Install

Docket is not on PyPI yet, so install it from a clone:

```bash
git clone https://github.com/rajmaurya0904/docket
cd docket
pip install -e .
```

## Usage

```bash
docket build docs -o site            # Markdown in docs/, HTML out in site/
docket build docs --base-url https://api.example.com --strict
docket check docs                    # validate links and example JSON, write nothing
docket serve site -p 8000            # static preview at http://127.0.0.1:8000/
```

`build` also takes `-t/--title`, `--clean` (empties the output first, but only if docket created it or it is empty) and `--no-search`. Exit codes: `0` success, `1` a build error (or warnings under `--strict`, or in `check`), `2` bad usage such as a missing source directory.

Document an endpoint by starting a heading with an HTTP method and a path. The text under it is mined by sub-heading:

````markdown
## POST /users

Create a new user.

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
{ "id": 3, "name": "Charlie" }
```
````

For a one-off endpoint you can use an `api` block instead (see `examples/api/health.md`):

````markdown
```api
GET /users/{id}
summary: Fetch one user
param verbose query boolean: Include extra fields
header Accept: application/json
response 200:
  { "id": 1, "name": "Alice" }
```
````

Page metadata is flat frontmatter: `title`, `description` and an integer `order` for sorting the sidebar.

## How it works

- **Discovery.** Every `.md` and `.markdown` file under the source folder is a page. Names starting with `.` or `_` are skipped. Other files (images, downloads) are copied across as they are.
- **Compilation.** A small Markdown parser builds a block tree (headings, lists, tables, fenced code, quotes, task lists) and renders it to HTML. Heading ids are unique per page and feed the on-page contents list.
- **Endpoint detection.** Headings shaped like `METHOD /path` and fenced `api` blocks become endpoint records. Path parameters written as `{id}` are added automatically, and example blocks tagged `json` are parsed, so invalid JSON becomes a warning.
- **Link rewriting.** `guide/intro.md`, `../index.md` and `/api/users` all resolve to the right relative `.html` path, so the output works from any folder and from `file://`. Links to missing pages or missing `#fragments` are reported.
- **Output.** Each page is a complete HTML document with a sidebar, light and dark themes and a mobile menu. The site also gets `assets/docket.css`, `assets/docket.js` and a small search index loaded as a script, so search works without a server.

## Limitations

- Markdown is a practical subset, not full CommonMark. Reference-style links, footnotes and link URLs containing parentheses are not handled. Raw HTML is passed through unchanged and unsanitised, so only build docs you trust.
- No syntax highlighting, no custom themes or templates, no live reload. `docket serve` is a plain static file server; rebuild after each change.
- Frontmatter is flat `key: value` only. Nested YAML is not understood: indented keys are read as top-level keys and list items are dropped.
- The explorer sends requests from your browser, so the target API must allow cross-origin requests (CORS). It sends the headers and body you see and nothing more: no OAuth flows, no request history, and it does not import OpenAPI files.
- Search is a substring match over page titles and the first 2000 characters of text, run in the browser.
- The explorer script is covered by Node-based unit tests of its URL, header and curl builders, and was exercised by hand in a browser against a local mock API. There is no automated browser test of the page itself.

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
```

The tests that run JavaScript need `node` on the path and are skipped without it.

## Licence

MIT. See [LICENSE](LICENSE).
