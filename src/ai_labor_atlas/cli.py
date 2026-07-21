from __future__ import annotations

import argparse
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .dashboard import write_site
from .demo import write_demo
from .io import read_csv, write_json
from .metrics import group_by_major_soc, rank_rows, summarize
from .pipeline import build_dataset
from .sources import download_registered_sources


ROOT = Path(__file__).resolve().parents[2]


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="AI Labor Atlas reproducible pipeline")
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("download", help="download sources with source registry")
    build = sub.add_parser("build", help="build canonical occupation output")
    build.add_argument(
        "--demo", action="store_true", help="build deterministic demo data"
    )
    analyze = sub.add_parser("analyze", help="summarize processed occupation data")
    analyze.add_argument("--top", type=int, default=10)
    search = sub.add_parser("search", help="search occupation titles and descriptions")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=20)
    sub.add_parser("serve", help="serve a dependency-free local dashboard")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    raw_dir = ROOT / "data" / "raw"
    processed_dir = ROOT / "data" / "processed"
    if args.command == "download":
        result = download_registered_sources(
            ROOT / "config" / "source_registry.json", raw_dir
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "build":
        if args.demo:
            write_demo(processed_dir / "occupations.csv")
            build_dataset(raw_dir, processed_dir, demo=True)
        else:
            build_dataset(raw_dir, processed_dir, demo=False)
        print(f"built {processed_dir / 'occupations.csv'}")
        return 0
    path = processed_dir / "occupations.csv"
    if not path.exists():
        print("No processed dataset found. Run: atlas build --demo", file=sys.stderr)
        return 2
    rows = read_csv(path)
    if args.command == "analyze":
        result = {
            "summary": summarize(rows),
            "groups": group_by_major_soc(rows),
            "top": rank_rows(rows)[: args.top],
        }
        write_json(processed_dir / "analysis.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "search":
        query = args.query.casefold()
        matches = [
            row
            for row in rows
            if query
            in f"{row.get('title', '')} {row.get('description', '')}".casefold()
        ]
        print(json.dumps(matches[: args.limit], ensure_ascii=False, indent=2))
        return 0
    if args.command == "serve":
        site_dir = ROOT / "site"
        write_site(site_dir, rows, summarize(rows), group_by_major_soc(rows))

        def handler(*handler_args, **handler_kwargs):
            return SimpleHTTPRequestHandler(
                *handler_args, directory=str(site_dir), **handler_kwargs
            )

        server = ThreadingHTTPServer(("127.0.0.1", 8765), handler)
        print("AI Labor Atlas running at http://127.0.0.1:8765")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
