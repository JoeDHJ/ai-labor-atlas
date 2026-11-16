"""Standalone research figures from the same selected evidence as the web case."""

from pathlib import Path

import matplotlib.pyplot as plt

from ai_labor_atlas.comparison import analyze_snapshot, load_snapshot
from ai_labor_atlas.workflow import run_workflow

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/reports"


def save(fig, stem):
    DEST.mkdir(parents=True, exist_ok=True)
    for extension in ("svg", "png"):
        fig.savefig(
            DEST / f"{stem}.{extension}",
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
        )
    plt.close(fig)


def main():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
        }
    )
    m = analyze_snapshot(load_snapshot())
    rows = m["occupations"]
    fig, ax = plt.subplots(figsize=(7.4, 6))
    ax.scatter(
        [r["ms_rank"] for r in rows],
        [r["claude_rank"] for r in rows],
        s=13,
        color="#176b64",
        alpha=0.3,
        edgecolors="none",
    )
    ax.plot([0, 100], [0, 100], color="#9faaa4", linestyle="--", linewidth=0.8)
    for code, offset in [
        ("19-3011", (-80, -32)),
        ("13-1071", (-100, -22)),
        ("15-1252", (-116, -12)),
        ("43-2021", (-20, 25)),
    ]:
        row = next(r for r in rows if r["soc"] == code)
        ax.scatter(row["ms_rank"], row["claude_rank"], s=25, color="#bc5428", zorder=3)
        ax.annotate(
            row["title"],
            (row["ms_rank"], row["claude_rank"]),
            xytext=offset,
            textcoords="offset points",
            fontsize=8,
            arrowprops={"arrowstyle": "-", "color": "#bc5428", "linewidth": 0.6},
        )
    ax.set(
        xlim=(-3, 103),
        ylim=(-3, 103),
        xlabel="Copilot applicability percentile",
        ylabel="Allocated Claude task-use percentile",
        title="Figure I. Occupation ranks differ across platform-based measures",
    )
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_yticks([0, 25, 50, 75, 100])
    fig.text(
        0.125,
        -0.015,
        "Notes: 758 equally weighted SOC occupations; average ranks for ties. Published aggregates from\ndifferent platforms and periods. Conversation share is not a worker adoption rate.\nSources: Microsoft Working with AI v1.1; Anthropic Economic Index, 2025-02-10; official O*NET crosswalks.",
        fontsize=8,
    )
    save(fig, "indicator-ranks")
    w = run_workflow()
    rows = w["strategies"]
    fig, ax = plt.subplots(figsize=(8, 5.2))
    names = [
        "Current\nworkflow",
        "AI without\ntraining",
        "AI +\ntraining",
        "AI + training\n+ reallocation",
        "Recruit\nanalyst",
        "AI + training\n+ recruit reviewer",
    ]
    bars = ax.bar(
        names,
        [r["accepted_cases"] for r in rows],
        color=["#889a94", "#d8ad94", "#74a59a", "#176b64", "#889a94", "#74a59a"],
        width=0.65,
    )
    bars[1].set_hatch("///")
    ax.bar_label(
        bars, labels=[f"{r['accepted_cases']:.1f}" for r in rows], padding=4, fontsize=9
    )
    ax.set(
        ylim=(0, 780),
        ylabel="Expected accepted briefs over 12 weeks",
        title="Figure II. Review capacity changes the value of AI task savings",
    )
    ax.tick_params(axis="x", labelsize=8)
    fig.text(
        0.125,
        -0.04,
        "Notes: Hypothetical team and parameters; not measured workplace effects. Hatched alternative fails\nthe 98% quality floor. Reallocation adds 40 role-qualification hours and begins in week 3. Default\ndemand is 60 cases/week. Costs and full parameters: workflow-assumptions.md.",
        fontsize=8,
    )
    save(fig, "workflow-capacity")


if __name__ == "__main__":
    main()
