"""Rebuild selected public evidence and its static site from acquired source files."""

from pathlib import Path

from ai_labor_atlas.comparison import analyze_snapshot, build_public_snapshot
from ai_labor_atlas.io import read_csv, read_json, write_json
from ai_labor_atlas.measurement_benchmark import build_benchmark
from ai_labor_atlas.workbench import write_workbench

ROOT = Path(__file__).resolve().parents[1]


def main():
    resources = ROOT / "src/ai_labor_atlas/resources"
    manifest = read_json(ROOT / "data/processed/data_manifest.json")
    if manifest.get("build", {}).get("mode") != "public_raw":
        raise ValueError(
            "Source-level public evidence build requires the actual public occupation dataset, not a demo"
        )
    snapshot = build_public_snapshot(ROOT / "data/raw", resources)
    full = analyze_snapshot(snapshot, read_csv(ROOT / "data/processed/occupations.csv"))
    write_json(resources / "aioe_comparison_summary.json", full["aioe_summary"])
    build_benchmark(ROOT / "data/raw/comparison", resources)
    # The selected packet excludes all occupation-level AIOE values and raw conversations.
    site = ROOT / "docs"
    result = write_workbench(site)
    print(result)


if __name__ == "__main__":
    main()
