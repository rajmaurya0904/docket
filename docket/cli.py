"""Command-line interface: ``docket build``, ``docket check`` and ``docket serve``."""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .builder import BuildError, BuildResult, SourceError, build

EXIT_OK = 0
EXIT_PROBLEMS = 1  # a build error, or warnings under --strict / check
EXIT_USAGE = 2


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docket",
        description="Build a static documentation site, with interactive API explorers, "
        "from a directory of Markdown files.",
    )
    parser.add_argument("--version", action="version", version=f"docket {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="command")

    b = sub.add_parser("build", help="build the site", description="Build the static site.")
    b.add_argument("source", type=Path, help="directory containing the Markdown files")
    b.add_argument(
        "-o", "--output", type=Path, default=Path("site"), help="output directory (default: site)"
    )
    b.add_argument(
        "-t", "--title", default="Documentation", help="site title (default: Documentation)"
    )
    b.add_argument("--base-url", default="", help="default API base URL for the explorers")
    b.add_argument("--clean", action="store_true", help="empty the output directory first")
    b.add_argument("--no-search", action="store_true", help="do not generate the search index")
    b.add_argument("--strict", action="store_true", help="exit with status 1 if there are warnings")

    c = sub.add_parser(
        "check",
        help="validate the docs without writing anything",
        description="Parse everything and report broken links and invalid examples.",
    )
    c.add_argument("source", type=Path, help="directory containing the Markdown files")

    s = sub.add_parser(
        "serve",
        help="serve a built site locally",
        description="Serve a built site over HTTP on localhost. It does not rebuild on change.",
    )
    s.add_argument(
        "directory", type=Path, nargs="?", default=Path("site"), help="built site (default: site)"
    )
    s.add_argument("-p", "--port", type=int, default=8000, help="port (default: 8000)")
    s.add_argument("--host", default="127.0.0.1", help="address to bind (default: 127.0.0.1)")
    return parser


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}{'' if n == 1 else 's'}"


def _report(result: BuildResult, stream=sys.stdout) -> None:
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    n = len(result.pages)
    print(
        f"{_count(n, 'page')}, {_count(result.endpoints, 'API endpoint')}, "
        f"{_count(len(result.warnings), 'warning')}",
        file=stream,
    )


def cmd_build(args: argparse.Namespace) -> int:
    result = build(
        args.source,
        args.output,
        site_title=args.title,
        base_url=args.base_url,
        clean=args.clean,
        search=not args.no_search,
    )
    for page in result.pages:
        print(f"  {page.source.as_posix():<28} -> {page.url}")
    _report(result)
    print(f"wrote {result.files_written} files to {args.output}")
    if args.strict and result.warnings:
        print("error: --strict was given and there are warnings", file=sys.stderr)
        return EXIT_PROBLEMS
    return EXIT_OK


def cmd_check(args: argparse.Namespace) -> int:
    result = build(args.source, None)
    _report(result)
    return EXIT_PROBLEMS if result.warnings else EXIT_OK


def cmd_serve(args: argparse.Namespace) -> int:
    directory: Path = args.directory
    if not directory.is_dir() or not (directory / "index.html").is_file():
        print(
            f"error: {directory} is not a built site (no index.html); run 'docket build' first",
            file=sys.stderr,
        )
        return EXIT_USAGE
    if not 0 < args.port < 65536:
        print(f"error: invalid port {args.port}", file=sys.stderr)
        return EXIT_USAGE
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer((args.host, args.port), handler) as httpd:
            print(f"serving {directory} at http://{args.host}:{args.port}/  (Ctrl+C to stop)")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nstopped")
    except OSError as exc:
        print(f"error: cannot listen on {args.host}:{args.port}: {exc.strerror}", file=sys.stderr)
        return EXIT_PROBLEMS
    return EXIT_OK


COMMANDS = {"build": cmd_build, "check": cmd_check, "serve": cmd_serve}


def main(argv: Sequence[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(sys.stderr)
        return EXIT_USAGE
    try:
        return COMMANDS[args.command](args)
    except SourceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_PROBLEMS


if __name__ == "__main__":
    sys.exit(main())
