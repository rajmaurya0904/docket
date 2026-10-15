# Docket

**A lightweight, zero-dependency Python tool that turns Markdown into fast, navigable documentation.**

Many documentation generators are slow, bloated, and require heavy dependencies, making it hard to iterate quickly and keep docs in sync with code.

They often force you to install large toolchains, rebuild entire sites for a single change, and struggle with modern markdown features.

## Example

<!-- A real command and its REAL pasted output. Run it first. -->

## Install

```bash
pip install -e ".[dev]"
```

## Usage

<!-- The 2-4 commands people actually need, one line each. -->

## How it works

<!-- 3-6 bullets: what it checks, computes or produces. -->

## Limitations

- Does not support custom HTML templates or theming; output is a fixed simple layout.
- No built‑in search or indexing; you need external tools for site search.
- Frontmatter parser only handles flat key‑value pairs; nested YAML structures are ignored.
- No live‑reload server; you must re‑run the generator after changes.
- Limited to Markdown input; other markup languages are not processed.
- Currently only generates static HTML; no JavaScript interactivity beyond basic navigation.

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
```

## License

MIT -- see [LICENSE](LICENSE).
