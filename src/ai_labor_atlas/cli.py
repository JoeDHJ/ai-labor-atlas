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
from .io import read_csv, read_json, write_json
from .llm_review import LLMNotConfiguredError, LLMReviewClient, LLMReviewError
from .metrics import aggregate_onet_rows, group_by_major_soc, rank_rows, summarize, summarize_tasks
from .occupation_context import (
    build_market_context,
    load_alias_registry,
    suggest_occupations,
    validate_alias_registry,
)
from .pipeline import build_dataset
from .reviews import load_reviews, summarize_reviews, validate_review_file
from .sources import SOURCE_INTEGRITY_FAILURE, download_registered_sources


ROOT = Path(__file__).resolve().parents[2]
LLM_REVIEW_CLIENT = LLMReviewClient()


def _read_json_body(headers, reader, max_bytes: int) -> dict[str, object]:
    """Read a bounded JSON request body without accepting invalid lengths."""

    length = int(headers.get("Content-Length", "0"))
    if length < 0 or length > max_bytes:
        raise ValueError("request body is too large")
    payload = json.loads(reader(length).decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("request body must be a JSON object")
    return payload


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
    validate = sub.add_parser(
        "validate-reviews",
        help="validate a public worker review import before serving",
    )
    validate.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/reviews.json"),
        metavar="PATH",
        help="JSON review import; defaults to data/processed/reviews.json",
    )
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
        return 2 if any(
            item.get("status") == SOURCE_INTEGRITY_FAILURE
            for item in result.get("results", [])
            if isinstance(item, dict)
        ) else 0
    if args.command == "build":
        try:
            if args.demo:
                write_demo(processed_dir / "occupations.csv")
                build_dataset(raw_dir, processed_dir, demo=True)
            else:
                build_dataset(raw_dir, processed_dir, demo=False)
        except ValueError as exc:
            print(f"Build validation error: {exc}", file=sys.stderr)
            return 2
        print(f"built {processed_dir / 'occupations.csv'}")
        return 0
    if args.command == "validate-reviews":
        review_path = (
            args.input if args.input.is_absolute() else ROOT / args.input
        )
        report = validate_review_file(review_path)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["valid"] else 2
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
        manifest_path = processed_dir / "data_manifest.json"
        try:
            manifest = read_json(manifest_path) if manifest_path.exists() else {}
            build_mode = (
                manifest.get("build", {}).get("mode")
                if isinstance(manifest, dict)
                and isinstance(manifest.get("build", {}), dict)
                else None
            )
            if build_mode != "demo":
                validate_alias_registry(load_alias_registry(), rows)
        except (TypeError, ValueError) as exc:
            print(f"Occupation alias release error: {exc}", file=sys.stderr)
            return 2
        try:
            reviews = load_reviews(processed_dir / "reviews.json")
        except ValueError as exc:
            print(f"Review import error: {exc}", file=sys.stderr)
            return 2
        release_codes = {
            str(row.get("onet_soc_code", "")).strip()
            for row in rows
            if str(row.get("onet_soc_code", "")).strip()
        }
        review_codes = {
            str(review.get("onet_soc_code", "")).strip()
            for review in reviews
            if str(review.get("onet_soc_code", "")).strip()
        }
        unknown_review_codes = sorted(review_codes - release_codes)
        if unknown_review_codes:
            print(
                "Review import error: occupation codes missing from this Atlas release: "
                + ", ".join(unknown_review_codes),
                file=sys.stderr,
            )
            return 2
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
            reviews,
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
                    payload = _read_json_body(self.headers, self.rfile.read, 80_000)
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
                if parsed.path == "/api/reviews":
                    source = parse_qs(parsed.query).get("occupation", [""])[0]
                    if not source:
                        self._send_json(
                            {
                                "error": "invalid_request",
                                "detail": "occupation is required",
                            },
                            status=400,
                        )
                        return
                    if not any(row.get("onet_soc_code") == source for row in rows):
                        self._send_json(
                            {
                                "error": "not_found",
                                "detail": "occupation code is not in this Atlas release",
                            },
                            status=404,
                        )
                        return
                    self._send_json(summarize_reviews(reviews, source))
                    return
                if parsed.path == "/api/occupation-context":
                    params = parse_qs(parsed.query)
                    source = params.get("source", [""])[0]
                    if source:
                        if params.get("query", [""])[0]:
                            self._send_json(
                                {
                                    "error": "invalid_request",
                                    "detail": "provide exactly one of source or query",
                                },
                                status=400,
                            )
                            return
                        matching_rows = [
                            row for row in rows if row.get("onet_soc_code") == source
                        ]
                        occupation = (
                            aggregate_onet_rows(matching_rows)[0]
                            if matching_rows
                            else None
                        )
                        if occupation is None:
                            self._send_json(
                                {
                                    "error": "not_found",
                                    "detail": "occupation code is not in this Atlas release",
                                },
                                status=404,
                            )
                            return
                        self._send_json(
                            {
                                "schema_version": "occupation_context.v0.3",
                                "occupation": occupation,
                                "market_context": build_market_context(
                                    occupation,
                                    tasks,
                                    bridge_engine.bridge(source),
                                    occupation_rows=matching_rows,
                                ),
                                "reviews": summarize_reviews(reviews, source),
                                "requires_confirmation": False,
                                "mapping_status": "user_confirmed",
                                "interpretation": "Worker comments are contextual evidence. They do not change Career Fit scores or Atlas measures.",
                            }
                        )
                        return
                    query = params.get("query", [""])[0]
                    try:
                        self._send_json(suggest_occupations(rows, query))
                    except ValueError as exc:
                        self._send_json(
                            {"error": "invalid_request", "detail": str(exc)},
                            status=400,
                        )
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
