"""Build a real-data, zero-install research case without network access."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .comparison import analyze_snapshot, load_snapshot
from .io import read_csv, read_json, write_csv, write_json
from .research_sql import QUERIES, build_warehouse
from .resources import resource_path
from .workflow import run_workflow


def write_workbench(directory: Path, *, local_mode: bool = False) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    measurement = analyze_snapshot(load_snapshot())
    measurement["aioe_summary"] = read_json(
        resource_path("aioe_comparison_summary.json")
    )
    tasks = defaultdict(list)
    for row in read_csv(resource_path("task_usage_links.csv")):
        tasks[row["soc"]].append(
            {
                "task": row["task"],
                "soc_count": int(row["soc_count"]),
                "allocated_share_pct": float(row["allocated_share_pct"]),
            }
        )
    examples = {
        soc: sorted(rows, key=lambda r: (-r["allocated_share_pct"], r["task"]))[:3]
        for soc, rows in tasks.items()
    }
    benchmark = read_json(resource_path("measurement_benchmark.json"))
    data = {
        "measurement": measurement,
        "benchmark": benchmark,
        "workflow": run_workflow(),
        "task_examples": examples,
        "local_mode": local_mode,
    }
    template = resource_path("workbench.html").read_text(encoding="utf-8")
    embedded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace(
        "<", "\\u003c"
    )
    (directory / "index.html").write_text(
        template.replace("__ATLAS_DATA__", embedded), encoding="utf-8"
    )
    for name in (
        "workbench.css",
        "workbench.js",
        "research-brief.md",
        "workflow-assumptions.md",
        "data-attribution.md",
        "measurement_benchmark.json",
    ):
        output_name = (
            "measurement-benchmark.json"
            if name == "measurement_benchmark.json"
            else name
        )
        (directory / output_name).write_bytes(resource_path(name).read_bytes())
    write_json(directory / "measurement-comparison.json", measurement)
    write_json(directory / "workflow-default.json", data["workflow"])
    fields = [
        "soc",
        "title",
        "ms_applicability",
        "claude_share_pct",
        "ms_rank",
        "claude_rank",
        "rank_gap_pp",
    ]
    write_csv(
        directory / "occupation-comparison.csv", measurement["occupations"], fields
    )
    (directory / "research-queries.sql").write_text(
        "\n\n".join("-- " + key + "\n" + query + ";" for key, query in QUERIES.items()),
        encoding="utf-8",
    )
    sql_results = build_warehouse(directory / "research.sqlite")
    write_json(directory / "sql-results.json", sql_results)
    write_json(
        directory / "site-manifest.json",
        {
            "release": "0.6.0",
            "occupation_source_mode": "public_aggregate_data",
            "organization_model": "hypothetical",
            "network_required": False,
            "common_soc_count": measurement["common_count"],
            "aioe_values_included": False,
            "files": sorted(
                [
                    "index.html",
                    "workbench.css",
                    "workbench.js",
                    "research-brief.md",
                    "workflow-assumptions.md",
                    "data-attribution.md",
                    "measurement-benchmark.json",
                    "measurement-comparison.json",
                    "workflow-default.json",
                    "occupation-comparison.csv",
                    "research-queries.sql",
                    "research.sqlite",
                    "sql-results.json",
                    "site-manifest.json",
                ]
            ),
        },
    )
    return {
        "common_soc_count": measurement["common_count"],
        "task_join": measurement["join"],
        "output": str(directory),
        "warehouse": str(directory / "research.sqlite"),
    }
