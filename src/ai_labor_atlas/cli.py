from __future__ import annotations

import argparse
import html
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
from .metrics import (
    aggregate_onet_rows,
    group_by_major_soc,
    rank_rows,
    summarize,
    summarize_tasks,
)
from .occupation_context import (
    build_market_context,
    load_alias_registry,
    suggest_occupations,
    validate_alias_registry,
)
from .pipeline import build_dataset
from .reviews import load_reviews, summarize_reviews, validate_review_file
from .runtime import config_path, data_root
from .sources import SOURCE_INTEGRITY_FAILURE, download_registered_sources
from .intelligence import build_research, refresh_market
from .research_dashboard import write_research_site
from .scenario import Scenario, run_scenario, sensitivity
from .staffing import refresh_staffing
from .workbench import write_workbench
from .workflow import Workflow, run_workflow


LLM_REVIEW_CLIENT = LLMReviewClient()

AIOE_DISPLAY_METADATA = {
    "scale": "0-100 relative display scale",
    "interpretation": (
        "Higher means relatively higher AIOE within this release. It is not a "
        "probability, replacement risk, or forecast of job loss."
    ),
}


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


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
    analyze.add_argument("--top", type=_non_negative_int, default=10)
    search = sub.add_parser("search", help="search occupation titles and descriptions")
    search.add_argument("query")
    search.add_argument("--limit", type=_non_negative_int, default=20)
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
    sub.add_parser(
        "market-update", help="explicitly refresh six public BLS/FRED monthly series"
    )
    sub.add_parser(
        "staffing-update",
        help="explicitly refresh four BLS 2025 industry staffing matrices",
    )
    sub.add_parser(
        "research", help="regenerate both labor-market intelligence cases and exports"
    )
    scenario = sub.add_parser(
        "scenario", help="run an explicit workforce capacity scenario"
    )
    for key, value in Scenario().__dict__.items():
        scenario.add_argument(
            "--" + key.replace("_", "-"),
            type=int if key == "years" else float,
            default=value,
        )
    scenario.add_argument("--output", type=Path, help="optional JSON result path")
    workbench = sub.add_parser(
        "workbench",
        help="export the real public-data research site and SQL warehouse offline",
    )
    workbench.add_argument("--output", type=Path, default=Path("data/workbench"))
    workflow = sub.add_parser(
        "workflow",
        help="compare task allocation, training and recruitment alternatives",
    )
    for key, value in Workflow().__dict__.items():
        workflow.add_argument(
            "--" + key.replace("_", "-"),
            type=int
            if key in {"weeks", "hiring_lead_weeks", "reallocation_delay_weeks"}
            else float,
            default=value,
        )
    workflow.add_argument("--output", type=Path)
    return root


def _main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    atlas_data_root = data_root()
    raw_dir = atlas_data_root / "raw"
    processed_dir = atlas_data_root / "processed"
    research_dir = atlas_data_root / "research"
    if args.command == "workbench":
        print(json.dumps(write_workbench(args.output), indent=2))
        return 0
    if args.command == "workflow":
        result = run_workflow(
            Workflow(**{k: getattr(args, k) for k in Workflow().__dict__})
        )
        if args.output:
            write_json(args.output, result)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "market-update":
        print(json.dumps(refresh_market(raw_dir, research_dir), indent=2))
        return 0
    if args.command == "staffing-update":
        print(json.dumps(refresh_staffing(raw_dir, research_dir), indent=2))
        return 0
    if args.command == "scenario":
        params = Scenario(**{key: getattr(args, key) for key in Scenario().__dict__})
        result = run_scenario(params)
        result["sensitivity"] = sensitivity(params)
        if args.output:
            write_json(args.output, result)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "download":
        try:
            result = download_registered_sources(
                config_path("source_registry.json"), raw_dir
            )
        except (OSError, TypeError, ValueError) as exc:
            print(f"Download error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return (
            2
            if any(
                item.get("status") in {SOURCE_INTEGRITY_FAILURE, "failed"}
                for item in result.get("results", [])
                if isinstance(item, dict)
            )
            else 0
        )
    if args.command == "build":
        try:
            if args.demo:
                write_demo(processed_dir / "occupations.csv")
                build_dataset(raw_dir, processed_dir, demo=True)
            else:
                build_dataset(raw_dir, processed_dir, demo=False)
        except (FileNotFoundError, PermissionError, RuntimeError, ValueError) as exc:
            print(f"Build validation error: {exc}", file=sys.stderr)
            return 2
        print(f"built {processed_dir / 'occupations.csv'}")
        return 0
    if args.command == "validate-reviews":
        review_path = (
            args.input if args.input.is_absolute() else Path.cwd() / args.input
        )
        if not review_path.exists():
            report = validate_review_file(review_path)
            report["valid"] = False
            report["error_count"] = 1
            report["errors"] = [
                {
                    "row": None,
                    "field": "file",
                    "message": f"review import does not exist: {review_path}",
                }
            ]
            report["note"] = "Create the file or pass the path to an existing import."
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 2
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
    if args.command == "research":
        result = build_research(raw_dir, processed_dir, research_dir)
        print(
            json.dumps(
                {
                    "mode": result["mode"],
                    "case1_soc_count": result["case1"]["sample_soc_count"],
                    "case1_wage_ratio": result["case1"]["high_low_wage_ratio"],
                    "market_observations": len(result["market_observations"]),
                    "skill_rows": len(result["case2"]["skills"]),
                    "output": str(research_dir),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "analyze":
        summary = summarize(rows)
        summary.update(summarize_tasks(rows, tasks))
        result = {
            "summary": summary,
            "groups": group_by_major_soc(rows),
            "top": rank_rows(rows)[: args.top],
            "ai_exposure_display": AIOE_DISPLAY_METADATA,
        }
        write_json(processed_dir / "analysis.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "search":
        query = args.query.casefold()
        matches = [
            {
                **row,
                "ai_exposure_interpretation": AIOE_DISPLAY_METADATA["interpretation"],
            }
            for row in rows
            if query
            in f"{row.get('title', '')} {row.get('description', '')}".casefold()
        ]
        # Keep the established list-shaped CLI contract: scripts commonly pipe this
        # command to JSON tooling.  Each result carries the plain-language AIOE
        # interpretation so people do not have to infer what the 0–100 display means.
        print(json.dumps(matches[: args.limit], ensure_ascii=False, indent=2))
        return 0
    if args.command == "serve":
        if not rows:
            raise ValueError(
                "Cannot serve an empty occupation dataset; run atlas build first"
            )
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
        site_dir = atlas_data_root / "site"
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
        (site_dir / "index.html").replace(site_dir / "explorer.html")
        # Keep the original explorer/API and put current research at the homepage.
        try:
            result = build_research(raw_dir, processed_dir, research_dir)
        except (FileNotFoundError, ValueError) as exc:
            # A processed-only installation can still use the established explorer/API.
            result = None
            for generated_file in (
                "research.json",
                "executive-brief.md",
                "exposure_quartiles.csv",
                "industry_changes.csv",
                "skill_composition.csv",
                "market_observations.csv",
                "industry_staffing.csv",
            ):
                (site_dir / generated_file).unlink(missing_ok=True)
            notice = html.escape(str(exc))
            (site_dir / "index.html").write_text(
                '<!doctype html><html lang="en"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                "<title>AI Labor Atlas 0.6.1</title><main><h1>Research data unavailable</h1>"
                f"<p>{notice}</p><p>Restore the required source layers and run "
                "<code>atlas research</code> to regenerate research findings.</p>"
                '<p><a href="explorer.html">Open the occupation explorer</a></p></main></html>',
                encoding="utf-8",
            )
            print(
                f"Research data unavailable: {exc}; occupation explorer/API remain available.",
                file=sys.stderr,
            )
        else:
            write_research_site(site_dir, result)

        (site_dir / "index.html").replace(site_dir / "market.html")
        write_workbench(site_dir, local_mode=True)

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
                if urlparse(self.path).path == "/api/scenario":
                    try:
                        payload = _read_json_body(self.headers, self.rfile.read, 16_000)
                        params = Scenario(**payload)
                        result = run_scenario(params)
                        result["sensitivity"] = sensitivity(params)
                        self._send_json(result)
                    except (TypeError, ValueError, json.JSONDecodeError) as exc:
                        self._send_json(
                            {"error": "invalid_scenario", "detail": str(exc)},
                            status=400,
                        )
                    return
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


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except (OSError, TypeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
