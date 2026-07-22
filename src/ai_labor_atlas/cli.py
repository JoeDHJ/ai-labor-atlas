from __future__ import annotations

import argparse
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .dashboard import write_site
from .demo import write_demo
from .distance import OccupationBridge
from .io import read_csv, write_json
from .llm_review import LLMNotConfiguredError, LLMReviewClient, LLMReviewError
from .metrics import group_by_major_soc, rank_rows, summarize, summarize_tasks
from .pipeline import build_dataset
from .sources import download_registered_sources


ROOT = Path(__file__).resolve().parents[2]
LLM_REVIEW_CLIENT = LLMReviewClient()


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
    tasks_path = processed_dir / "tasks.csv"
    tasks = read_csv(tasks_path) if tasks_path.exists() else []
    if args.command == "analyze":
        summary = summarize(rows)
        summary.update(summarize_tasks(rows, tasks))
        result = {
            "summary": summary,
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
        summary = summarize(rows)
        summary.update(summarize_tasks(rows, tasks))
        bridge_engine = OccupationBridge(raw_dir, rows, tasks)
        default_code = next(
            (
                row["onet_soc_code"]
                for row in rows
                if row.get("title", "").casefold() == "data scientists"
            ),
            rows[0].get("onet_soc_code", "") if rows else "",
        )
        write_site(
            site_dir,
            rows,
            summary,
            group_by_major_soc(rows),
            tasks,
            bridge_engine.bridge(default_code) if default_code else None,
        )

        class AtlasHandler(SimpleHTTPRequestHandler):
            def __init__(self, *handler_args, **handler_kwargs):
                super().__init__(
                    *handler_args, directory=str(site_dir), **handler_kwargs
                )

            def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:
                if urlparse(self.path).path != "/api/deep-review":
                    self._send_json({"error": "not_found"}, status=404)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length > 80_000:
                        raise ValueError("request body is too large")
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                    occupation = payload.get("occupation", {})
                    candidates = payload.get("candidates", [])
                    if not isinstance(occupation, dict) or not isinstance(
                        candidates, list
                    ):
                        raise TypeError(
                            "occupation must be an object and candidates must be a list"
                        )
                    result = LLM_REVIEW_CLIENT.review_occupation(
                        occupation, candidates[:10]
                    )
                except LLMNotConfiguredError as exc:
                    self._send_json(
                        {"error": "not_configured", "detail": str(exc)}, status=503
                    )
                    return
                except LLMReviewError as exc:
                    self._send_json(
                        {"error": "review_failed", "detail": str(exc)}, status=502
                    )
                    return
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    self._send_json(
                        {"error": "invalid_request", "detail": str(exc)}, status=400
                    )
                    return
                self._send_json(result)

            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path == "/favicon.ico":
                    self.send_response(204)
                    self.end_headers()
                    return
                if parsed.path == "/api/bridge":
                    source = parse_qs(parsed.query).get("source", [""])[0]
                    if not source:
                        self._send_json(
                            {
                                "error": "invalid_request",
                                "detail": "source is required",
                            },
                            status=400,
                        )
                        return
                    self._send_json(bridge_engine.bridge(source))
                    return
                super().do_GET()

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 8765), AtlasHandler)
        print("AI Labor Atlas running at http://127.0.0.1:8765")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
