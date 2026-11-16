"""Regenerate selected public portfolio exhibits after `atlas research`.

Haojian Dui. Inputs: data/research/research.json. Outputs: docs/reports/.
Install the optional reports extra for matplotlib. No Word/PDF output is created.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ai_labor_atlas.intelligence import csv_text, executive_brief

ROOT = Path(__file__).resolve().parents[1]


def main():
    result = json.loads(
        (ROOT / "data/research/research.json").read_text(encoding="utf-8")
    )
    if result["mode"] != "public_data":
        raise ValueError(
            "Public portfolio exhibits require the actual public-data occupation build"
        )
    output = ROOT / "docs/reports"
    output.mkdir(parents=True, exist_ok=True)
    (output / "executive-brief.md").write_text(
        executive_brief(result), encoding="utf-8"
    )
    for name, rows in (
        ("exposure_quartiles.csv", result["case1"]["quartiles"]),
        ("industry_changes.csv", result["case2"]["market_comparison"]),
        ("skill_composition.csv", result["case2"]["skills"]),
    ):
        (output / name).write_text(csv_text(rows), encoding="utf-8")
    # Only selected aggregate evidence enters this directory; no AIOE occupation rows.
    packet = {
        "schema_version": "portfolio.v1",
        "version": result["version"],
        "mode": result["mode"],
        "case1": result["case1"],
        "case2": {k: v for k, v in result["case2"].items() if k != "industry_staffing"},
        "coverage": result["coverage"],
        "aioe_display": result["aioe_display"],
    }
    (output / "selected-evidence.json").write_text(
        json.dumps(packet, indent=2), encoding="utf-8"
    )
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.18,
            "axes.axisbelow": True,
            "savefig.facecolor": "white",
            "svg.fonttype": "none",
        }
    )
    fig, ax = plt.subplots(figsize=(8, 4.4), layout="constrained")
    quartiles = result["case1"]["quartiles"]
    bars = ax.bar(
        [f"Q{r['quartile']}" for r in quartiles],
        [r["weighted_occupation_median_wage"] / 1000 for r in quartiles],
        color=["#6589b4"] * 3 + ["#177e89"],
        width=0.65,
    )
    ax.bar_label(bars, fmt="$%.1fk", padding=5)
    ax.set_ylim(0, 105)
    ax.set(
        xlabel="AI exposure quartile (equal occupation counts)",
        ylabel="Weighted occupation median wage, thousand USD/year",
        title="Figure I. Exposure and occupational wage levels",
    )
    fig.text(
        0.14,
        -0.02,
        "OEWS May 2025; 691 complete SOCs; each SOC weighted by employment once.\nDescriptive comparison; occupation medians are not the pooled worker median.",
        fontsize=8,
    )
    fig.savefig(output / "exposure-wages.svg", bbox_inches="tight")
    fig.savefig(output / "exposure-wages.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.3), layout="constrained")
    comparisons = result["case2"]["market_comparison"]
    start, end = comparisons[0]["start_period"], comparisons[0]["end_period"]
    labels = {
        "job_openings": "Job openings",
        "payroll_employment": "Payroll employment",
        "hourly_earnings": "Nominal hourly earnings",
    }
    for ax, metric in zip(axes, labels):
        for index, summary in enumerate(
            r for r in comparisons if r["metric"] == metric
        ):
            records = [
                r
                for r in result["market_observations"]
                if r["source_id"] == summary["source_id"]
                and start <= r["period"] <= end
                and r["value"] is not None
            ]
            records.sort(key=lambda r: r["period"])
            dates = [datetime.strptime(r["period"], "%Y-%m") for r in records]
            ax.plot(
                dates,
                [100 * r["value"] / records[0]["value"] for r in records],
                color=("#177e89", "#4368a4")[index],
                linestyle=("-", "--")[index],
                label=summary["industry"],
                linewidth=2,
            )
        ax.set(title=labels[metric], ylabel="January 2022 = 100")
        ax.tick_params(axis="x", rotation=35)
    handles, names = axes[0].get_legend_handles_labels()
    fig.legend(handles, names, loc="outside lower center", ncol=2, frameon=False)
    fig.suptitle(f"Figure II. Industry market conditions, {start} to {end}")
    fig.savefig(output / "industry-trends.svg", bbox_inches="tight")
    fig.savefig(output / "industry-trends.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    industries = [
        r for r in result["case2"]["bundles"] if "(industry)" in r["occupation_group"]
    ]
    fig, ax = plt.subplots(figsize=(8, 4.4), layout="constrained")
    bars = ax.barh(
        [
            r["occupation_group"]
            .replace(" (industry)", "")
            .replace(" and business", " & business")
            for r in industries
        ],
        [100 * r["share_of_covered_employment"] for r in industries],
        color=["#4368a4", "#177e89"],
        height=0.55,
    )
    ax.bar_label(bars, fmt="%.1f%%", padding=6)
    ax.set(
        xlim=(0, 65),
        xlabel="Percent of covered industry employment",
        title="Figure III. Critical Thinking + Active Listening, both ≥ 3.5/5",
    )
    fig.text(
        0.1,
        -0.02,
        "O*NET 30.3; BLS 2025 staffing baseline. Employment coverage: manufacturing 85.8%;\nprofessional/business services 91.2%. Descriptive co-occurrence, not economic complementarity.",
        fontsize=8,
    )
    fig.savefig(output / "industry-skill-bundle.svg", bbox_inches="tight")
    fig.savefig(output / "industry-skill-bundle.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(
        "Regenerated selected public evidence, brief, three CSVs and three figure pairs."
    )


if __name__ == "__main__":
    main()
