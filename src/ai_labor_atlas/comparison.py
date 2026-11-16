"""Comparable occupation ranks with explicit constructs and mass-conserving task joins."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import correlation, mean

from .intelligence import unique_soc
from .io import read_csv, read_json, write_csv, write_json
from .resources import resource_path
from .pipeline import _load_crosswalk


def normalize_task(text: str) -> str:
    # No fuzzy/semantic match: punctuation and wording changes stay unmatched.
    return " ".join(text.casefold().split())


def allocate_tasks(
    mappings: list[dict], statements: list[dict], crosswalk: dict
) -> dict:
    """Equal fractional allocation across distinct detailed SOC parents per exact task.

    Task wording is the released usage key, not a time-use weight or worker identity.
    Multiple O*NET children within one parent do not receive extra conversation mass.
    """
    links = defaultdict(set)
    titles = {}
    excluded = set()
    for row in statements:
        source_code = row["O*NET-SOC Code"]
        key = normalize_task(row["Task"])
        targets = crosswalk.get(source_code, [])
        if not targets:
            excluded.add(source_code)
        for code in targets:
            if not re.fullmatch(r"\d{2}-\d{4}", code):
                raise ValueError("Invalid source SOC parent")
            links[key].add(code)
            titles.setdefault(code, row["Title"])
    usage, task_rows, seen = defaultdict(float), [], set()
    total = unmatched = 0.0
    for row in mappings:
        key = normalize_task(row["task_name"])
        value = float(row["pct"])
        if key in seen or not math.isfinite(value) or value < 0:
            raise ValueError("Duplicate or invalid task usage")
        seen.add(key)
        total += value
        parents = sorted(links.get(key, []))
        if not parents:
            unmatched += value
            continue
        for soc in parents:
            share = value / len(parents)
            usage[soc] += share
            task_rows.append(
                {
                    "soc": soc,
                    "task": key,
                    "source_share_pct": value,
                    "soc_count": len(parents),
                    "allocated_share_pct": share,
                }
            )
    allocated = sum(usage.values())
    if not math.isclose(total, allocated + unmatched, abs_tol=1e-8):
        raise ValueError("Conversation mass was not conserved")
    # Zero means no released matched task usage in the source task universe only.
    occupations = [
        {
            "soc": code,
            "source_title": titles[code],
            "claude_share_pct": usage[code],
            "source_task_count": sum(code in socs for socs in links.values()),
        }
        for code in sorted(titles)
    ]
    return {
        "occupations": occupations,
        "tasks": task_rows,
        "join": {
            "released_task_count": len(mappings),
            "matched_task_count": len({r["task"] for r in task_rows}),
            "source_task_universe": len(links),
            "released_share_pct": total,
            "allocated_share_pct": allocated,
            "unmatched_share_pct": unmatched,
            "unmapped_onet_codes": sorted(excluded),
            "shared_task_count": sum(len(links[k]) > 1 for k in seen if k in links),
        },
    }


def fractional_ranks(values: dict[str, float]) -> dict[str, float]:
    """Average ranks for ties, converted to 0..100 common-sample percentiles."""
    grouped = defaultdict(list)
    for code, value in values.items():
        if not math.isfinite(value):
            raise ValueError("Ranks require finite values")
        grouped[value].append(code)
    result, offset = {}, 0
    for value in sorted(grouped):
        codes = grouped[value]
        rank = offset + (len(codes) - 1) / 2
        for code in codes:
            result[code] = 100 * rank / (len(values) - 1) if len(values) > 1 else 50.0
        offset += len(codes)
    return result


def rank_comparison(rows: list[dict], left: str, right: str) -> dict:
    common = [r for r in rows if r.get(left) is not None and r.get(right) is not None]
    a = fractional_ranks({r["soc"]: r[left] for r in common})
    b = fractional_ranks({r["soc"]: r[right] for r in common})
    # Population-description only: no standard error/p-value invented for released aggregates.
    av, bv = list(a.values()), [b[k] for k in a]
    rho = (
        correlation(av, bv)
        if len(common) > 1 and len(set(av)) > 1 and len(set(bv)) > 1
        else None
    )
    return {
        "left": left,
        "right": right,
        "sample_count": len(common),
        "spearman_rho": rho,
        "mean_absolute_rank_gap_pp": mean(abs(a[k] - b[k]) for k in a) if a else None,
        "top_quartile_overlap_count": sum(a[k] >= 75 and b[k] >= 75 for k in a),
        "left_top_quartile_count": sum(v >= 75 for v in a.values()),
        "right_top_quartile_count": sum(v >= 75 for v in b.values()),
    }


def build_public_snapshot(raw_dir: Path, target: Path) -> dict:
    raw = raw_dir / "comparison"
    current = _load_crosswalk(raw_dir)
    legacy = defaultdict(set)
    for row in read_csv(raw / "onet_2010_to_2019.csv"):
        for code in current.get(row["O*NET-SOC 2019 Code"], []):
            legacy[row["O*NET-SOC 2010 Code"]].add(code)
    allocated = allocate_tasks(
        read_csv(raw / "anthropic_task_mappings.csv"),
        read_csv(raw / "anthropic_task_statements.csv"),
        legacy,
    )
    ms = {r["SOC Code"]: r for r in read_csv(raw / "microsoft_scores.csv")}
    occupations = []
    for row in allocated["occupations"]:
        score = ms.get(row["soc"])
        if score:
            row["title"] = score["title"]
            row["ms_applicability"] = float(score["ai_applicability_score"])
            if not 0 <= row["ms_applicability"] <= 1:
                raise ValueError("Applicability out of bounds")
            occupations.append(row)
    manifest = read_json(raw / "manifest.json")
    result = {
        "schema": "atlas.measurement.v1",
        "mode": "public_aggregate_data",
        "microsoft_count": len(ms),
        "anthropic_soc_count": len(allocated["occupations"]),
        "common_count": len(occupations),
        "join": allocated["join"],
        "provenance": manifest,
        "occupations": occupations,
        "comparison": rank_comparison(
            occupations, "ms_applicability", "claude_share_pct"
        ),
    }
    source_occupations = {
        r["soc"]: {
            "soc": r["soc"],
            "title": r["source_title"],
            "claude_share_pct": r["claude_share_pct"],
            "ms_applicability": None,
        }
        for r in allocated["occupations"]
    }
    for soc, row in ms.items():
        source_occupations.setdefault(soc, {"soc": soc, "claude_share_pct": None})
        source_occupations[soc].update(
            title=row["title"], ms_applicability=float(row["ai_applicability_score"])
        )
    result["source_occupations"] = list(source_occupations.values())
    positive = [r for r in occupations if r["claude_share_pct"] > 0]
    result["positive_use_comparison"] = rank_comparison(
        positive, "ms_applicability", "claude_share_pct"
    )
    result["zero_use_soc_count"] = len(occupations) - len(positive)
    # Allocation sensitivity: retain only wording that has one distinct target SOC.
    exclusive = defaultdict(float)
    for row in allocated["tasks"]:
        if row["soc_count"] == 1:
            exclusive[row["soc"]] += row["allocated_share_pct"]
    alternative = [
        dict(r, exclusive_share_pct=exclusive[r["soc"]]) for r in occupations
    ]
    result["exclusive_task_sensitivity"] = rank_comparison(
        alternative, "ms_applicability", "exclusive_share_pct"
    )
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / "measurement_snapshot.json", result)
    write_csv(
        target / "task_usage_links.csv",
        allocated["tasks"],
        ["soc", "task", "source_share_pct", "soc_count", "allocated_share_pct"],
    )
    return result


def load_snapshot() -> dict:
    return read_json(resource_path("measurement_snapshot.json"))


def analyze_snapshot(snapshot: dict, local_rows: list[dict] | None = None) -> dict:
    rows = [dict(r) for r in snapshot["occupations"]]
    a = fractional_ranks({r["soc"]: r["ms_applicability"] for r in rows})
    b = fractional_ranks({r["soc"]: r["claude_share_pct"] for r in rows})
    for row in rows:
        row.update(
            ms_rank=a[row["soc"]],
            claude_rank=b[row["soc"]],
            rank_gap_pp=b[row["soc"]] - a[row["soc"]],
        )
    result = {k: v for k, v in snapshot.items() if k != "occupations"}
    result["occupations"] = rows
    result["largest_gaps"] = sorted(rows, key=lambda r: -abs(r["rank_gap_pp"]))[:12]
    if local_rows is not None:
        aioe = {
            r["soc_2018_code"]: r["ai_exposure_source_raw"]
            for r in unique_soc(local_rows)
            if r.get("ai_exposure_source_raw") is not None
        }
        joined = [dict(r, aioe_raw=aioe.get(r["soc"])) for r in rows]
        complete = [r for r in joined if r["aioe_raw"] is not None]
        result["aioe_summary"] = {
            "common_three_count": len(complete),
            "excluded_public_common": len(rows) - len(complete),
            "comparisons": [
                rank_comparison(complete, "aioe_raw", key)
                for key in ("ms_applicability", "claude_share_pct")
            ]
            + [rank_comparison(complete, "ms_applicability", "claude_share_pct")],
            "public_data_note": "Only aggregate AIOE comparisons are published; occupation values stay local.",
        }
    return result
