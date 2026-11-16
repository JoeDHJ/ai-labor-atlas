"""Reproducible public labor-market cases and portfolio.v1 snapshots.

No network work happens during analysis or serving. Refresh is a separate command.
"""

from __future__ import annotations

import csv
import io
import math
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean

from .io import read_csv, read_json, write_csv, write_json
from .pipeline import _find_file, _load_crosswalk, _number, _read_tsv
from .resources import resource_path
from .sources import download_file
from .staffing import aggregate_staffing, load_staffing

SCHEMA = "portfolio.v1"
SERIES = (
    (
        "JTS540099JOL",
        "Professional and business services",
        "54-56",
        "job_openings",
        "thousand_jobs",
    ),
    ("JTS3000JOL", "Manufacturing", "31-33", "job_openings", "thousand_jobs"),
    (
        "USPBS",
        "Professional and business services",
        "54-56",
        "payroll_employment",
        "thousand_jobs",
    ),
    ("MANEMP", "Manufacturing", "31-33", "payroll_employment", "thousand_jobs"),
    (
        "CES6000000003",
        "Professional and business services",
        "54-56",
        "hourly_earnings",
        "USD_per_hour_nominal",
    ),
    (
        "CES3000000003",
        "Manufacturing",
        "31-33",
        "hourly_earnings",
        "USD_per_hour_nominal",
    ),
)
MARKET_FIELDS = [
    "schema_version",
    "source_id",
    "source_url",
    "retrieved_at",
    "source_vintage",
    "geography",
    "unit_of_observation",
    "period",
    "industry",
    "industry_id",
    "industry_taxonomy",
    "metric",
    "value",
    "unit",
    "currency",
    "price_year",
    "seasonal_adjustment",
    "status",
]


def series_manifest() -> dict[str, object]:
    return {
        "schema_version": SCHEMA,
        "start_period": "2022-01",
        "sources": [
            {
                "source_id": sid,
                "source_url": f"https://fred.stlouisfed.org/series/{sid}",
                "download_url": f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=2022-01-01",
                "industry": industry,
                "industry_id": code,
                "metric": metric,
                "unit": unit,
                "provider": "U.S. Bureau of Labor Statistics via FRED, Federal Reserve Bank of St. Louis",
                "frequency": "monthly",
                "seasonal_adjustment": "SA",
                "license": "Public domain; source citation requested",
            }
            for sid, industry, code, metric, unit in SERIES
        ],
    }


def parse_series(path: Path, source: dict, retrieved_at: str) -> list[dict]:
    """Validate identity, dates, duplicate keys and numeric cells before using a series."""
    sid = source["source_id"]
    values = read_csv(path)
    if not values or sid not in values[0] or "observation_date" not in values[0]:
        raise ValueError(f"{sid}: missing expected CSV columns or empty source")
    seen, output = set(), []
    for row in values:
        day = date.fromisoformat(row["observation_date"])
        if day.day != 1 or day > date.today():
            raise ValueError(f"{sid}: invalid monthly observation date")
        if day in seen:
            raise ValueError(f"{sid}: duplicate monthly observation")
        seen.add(day)
        if day < date(2022, 1, 1):
            continue
        raw = row[sid]
        value = None if raw in ("", ".") else float(raw)
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError(f"{sid}: nonfinite or negative source value")
        output.append(
            {
                "schema_version": SCHEMA,
                "source_id": sid,
                "source_url": source["source_url"],
                "retrieved_at": retrieved_at,
                "source_vintage": retrieved_at[:10],
                "geography": "US",
                "unit_of_observation": "industry_month",
                "period": day.isoformat()[:7],
                "industry": source["industry"],
                "industry_id": source["industry_id"],
                "industry_taxonomy": "BLS industry supersector (NAICS 2022 grouping)",
                "metric": source["metric"],
                "value": value,
                "unit": source["unit"],
                "currency": "USD" if source["metric"] == "hourly_earnings" else "",
                "price_year": "current observation month"
                if source["metric"] == "hourly_earnings"
                else "",
                "seasonal_adjustment": "SA",
                "status": "observed",
            }
        )
    if not output:
        raise ValueError(f"{sid}: no observations from 2022 onward")
    return sorted(output, key=lambda row: row["period"])


def refresh_market(raw_dir: Path, destination: Path, *, fetch: bool = True) -> dict:
    records, provenance = [], []
    for source in series_manifest()["sources"]:
        path = raw_dir / f"{source['source_id']}.csv"
        if fetch:
            # Validate a candidate before replacing the prior local business version.
            candidate = path.with_suffix(".candidate.csv")
            result = download_file(source["download_url"], candidate, retries=2)
            if result["status"] != "downloaded":
                raise ValueError(f"{source['source_id']}: {result.get('error')}")
            retrieved = str(result["retrieved_at"])
            parsed = parse_series(candidate, source, retrieved)
            if path.exists():
                previous = path.with_suffix(".previous.csv")
                if not previous.exists():
                    previous.write_bytes(path.read_bytes())
            candidate.replace(path)
        else:
            retrieved = datetime.fromtimestamp(
                path.stat().st_mtime, timezone.utc
            ).isoformat()
            parsed = parse_series(path, source, retrieved)
        records.extend(parsed)
        provenance.append(
            {
                **source,
                "path": str(path),
                "file_bytes": path.stat().st_size,
                "retrieved_at": retrieved,
                "row_count": len(parsed),
                "first_period": parsed[0]["period"],
                "last_period": parsed[-1]["period"],
            }
        )
    # Publish the complete panel only after all six sources validated.
    write_csv(destination / "market_observations.csv", records, MARKET_FIELDS)
    manifest = {
        "schema_version": SCHEMA,
        "row_count": len(records),
        "sources": provenance,
        "note": "Current retrieval vintage; historical observations may be revised.",
    }
    write_json(destination / "market_manifest.json", manifest)
    return manifest


def load_market(research_dir: Path) -> list[dict]:
    path = research_dir / "market_observations.csv"
    if not path.exists():
        path = resource_path("market_observations.csv")
    rows = read_csv(path)
    seen = set()
    registry = {row["source_id"]: row for row in series_manifest()["sources"]}
    for row in rows:
        if not set(MARKET_FIELDS).issubset(row):
            raise ValueError("market snapshot is missing required provenance columns")
        source = registry.get(row["source_id"])
        if (
            source is None
            or row["schema_version"] != SCHEMA
            or row["geography"] != "US"
        ):
            raise ValueError("unrecognized market snapshot identity/schema/geography")
        if any(
            row[field] != source[field] for field in ("metric", "unit", "industry_id")
        ):
            raise ValueError(
                "market snapshot units or industry do not match the registered source"
            )
        if (
            row["source_url"] != source["source_url"]
            or row["status"] != "observed"
            or row["seasonal_adjustment"] != "SA"
            or row["unit_of_observation"] != "industry_month"
        ):
            raise ValueError(
                "market snapshot source/status/observation metadata is invalid"
            )
        try:
            day = date.fromisoformat(row["period"] + "-01")
        except ValueError as exc:
            raise ValueError("invalid market snapshot monthly period") from exc
        if day < date(2022, 1, 1) or day > date.today():
            raise ValueError("market snapshot period is outside the supported window")
        key = row["source_id"], row["period"]
        if key in seen:
            raise ValueError("duplicate market observation key")
        seen.add(key)
        raw = row.get("value")
        value = None if raw in (None, "", ".") else float(raw)
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError("market snapshot value must be finite and nonnegative")
        row["value"] = value
    return rows


def unique_soc(rows: list[dict]) -> list[dict]:
    """Retain each SOC's market quantity once; never sum O*NET children."""
    groups = defaultdict(list)
    for row in rows:
        code = str(row.get("soc_2018_code", ""))
        if code:
            groups[code].append(row)
    result = []
    numeric = (
        "ai_exposure",
        "ai_exposure_source_raw",
        "employment_2024",
        "median_annual_wage",
        "annual_openings_2024_2034",
        "employment_change_2024_2034_pct",
    )
    for code, group in sorted(groups.items()):
        item = dict(group[0])
        for field in numeric:
            values = {_number(row.get(field)) for row in group} - {None}
            if len(values) > 1:
                raise ValueError(
                    f"Conflicting {field} within SOC {code}; resolve before analysis"
                )
            item[field] = next(iter(values), None)
        item["onet_children"] = len({r["onet_soc_code"] for r in group})
        item["onet_titles"] = sorted({str(r.get("title", "")) for r in group})
        result.append(item)
    return result


def _weighted(
    rows: list[dict], field: str, weight: str = "employment_2024"
) -> float | None:
    valid = [
        (r[field], r.get(weight))
        for r in rows
        if r.get(field) is not None and r.get(weight) is not None and r[weight] > 0
    ]
    return sum(v * w for v, w in valid) / sum(w for _, w in valid) if valid else None


def exposure_case(rows: list[dict]) -> dict:
    socs = unique_soc(rows)
    complete = [
        r
        for r in socs
        if r["ai_exposure"] is not None
        and r["median_annual_wage"] is not None
        and (r["employment_2024"] or 0) > 0
    ]
    complete.sort(key=lambda r: (r["ai_exposure"], r["soc_2018_code"]))
    if len(complete) < 4:
        raise ValueError(
            "Exposure case needs at least four complete unique SOC observations"
        )
    groups = []
    for quartile in range(4):
        subset = complete[
            len(complete) * quartile // 4 : len(complete) * (quartile + 1) // 4
        ]
        groups.append(
            {
                "quartile": quartile + 1,
                "occupation_count": len(subset),
                "employment_jobs": sum(r["employment_2024"] for r in subset),
                "exposure_min": subset[0]["ai_exposure"],
                "exposure_max": subset[-1]["ai_exposure"],
                "weighted_exposure": _weighted(subset, "ai_exposure"),
                "weighted_occupation_median_wage": _weighted(
                    subset, "median_annual_wage"
                ),
                "mean_occupation_median_wage": mean(
                    r["median_annual_wage"] for r in subset
                ),
            }
        )
    return {
        "question": "How do wage levels and employment differ across occupational AI exposure?",
        "status": "estimated",
        "design": "descriptive cross-section; equal-count SOC quartiles",
        "sample_soc_count": len(complete),
        "all_soc_count": len(socs),
        "excluded_soc_count": len(socs) - len(complete),
        "covered_employment_jobs": sum(r["employment_2024"] for r in complete),
        "quartiles": groups,
        "high_low_wage_ratio": groups[3]["weighted_occupation_median_wage"]
        / groups[0]["weighted_occupation_median_wage"],
        "note": "Employment-weighted average of occupation medians, not the median wage of all workers. OEWS May 2025; nominal USD/year. Sampling covariance is unavailable; no inferential or causal claim is made.",
    }


def skill_composition(
    raw_dir: Path,
    rows: list[dict],
    *,
    demo: bool,
    bundles: list[dict] | None = None,
    staffing: list[dict] | None = None,
) -> list[dict]:
    """Employment-weighted SOC profiles with an explicit equal-child crosswalk."""
    socs = unique_soc(rows)
    mapping = (
        _load_crosswalk(raw_dir)
        if not demo
        else {r["onet_soc_code"]: [r["soc_2018_code"]] for r in rows}
    )
    profiles = defaultdict(dict)
    for name in ("Essential Skills.txt", "Transferable Skills.txt"):
        path = _find_file(raw_dir, [name]) if not demo else None
        if path:
            for row in _read_tsv(path):
                value = _number(row.get("Data Value"))
                if row.get("Scale ID") == "IM" and value is not None:
                    profiles[row["O*NET-SOC Code"]][row["Element ID"]] = (
                        row["Element Name"],
                        value,
                    )
    if demo:
        # Deliberate test fixture; no synthetic rating is represented as a public observation.
        for index, r in enumerate(rows):
            profiles[r["onet_soc_code"]] = {
                "2.A.1.b": ("Active Listening", 2.5 + index % 3 * 0.5),
                "2.A.2.a": ("Critical Thinking", 3.0 + index % 2 * 0.6),
                "2.B.3.e": ("Programming", 1.2 + index % 4 * 0.7),
            }
    target = defaultdict(lambda: defaultdict(list))
    for onet, elements in profiles.items():
        targets = mapping.get(onet, [])
        if len(set(targets)) != 1:
            continue  # No arbitrary allocation of multi-target ratings into the research case.
        for element, (label, value) in elements.items():
            target[targets[0]][element].append((label, value))
    labels = {
        "15": "Computer and mathematical",
        "43": "Office and administrative support",
        "51": "Production",
    }
    output = []
    datasets = {}
    for major, group_name in labels.items():
        subset = [
            r
            for r in socs
            if str(r["soc_2018_code"]).startswith(major + "-")
            and (r["employment_2024"] or 0) > 0
        ]
        total = sum(r["employment_2024"] for r in subset)
        datasets[group_name] = (
            subset,
            total,
            major,
            "OEWS May 2025 national employment",
        )
    if staffing and not demo:
        for industry, (subset, total) in aggregate_staffing(staffing).items():
            datasets[industry + " (industry)"] = (
                subset,
                total,
                "",
                "BLS matrix 2025 industry baseline",
            )
    for group_name, (subset, total, major, weight_source) in datasets.items():
        if bundles is not None:
            left, right = "2.A.2.a", "2.A.1.b"  # Critical Thinking; Active Listening
            valid_pairs = [
                (r, target[r["soc_2018_code"]])
                for r in subset
                if left in target[r["soc_2018_code"]]
                and right in target[r["soc_2018_code"]]
            ]
            pair_denominator = sum(r["employment_2024"] for r, _ in valid_pairs)
            both = sum(
                r["employment_2024"]
                for r, ratings in valid_pairs
                if mean(v for _, v in ratings[left]) >= 3.5
                and mean(v for _, v in ratings[right]) >= 3.5
            )
            bundles.append(
                {
                    "occupation_group": group_name,
                    "skill_ids": [left, right],
                    "label": "Critical Thinking + Active Listening",
                    "threshold": 3.5,
                    "share_of_covered_employment": both / pair_denominator
                    if pair_denominator
                    else None,
                    "covered_employment_jobs": pair_denominator,
                    "employment_coverage": pair_denominator / total if total else None,
                    "employment_reference": weight_source,
                    "status": "synthetic" if demo else "estimated",
                    "interpretation": "Both average SOC importance ratings meet the threshold; descriptive skill co-occurrence, not economic complementarity.",
                }
            )
        element_ids = {k for r in subset for k in target[r["soc_2018_code"]]}
        for element in sorted(element_ids):
            valid = [
                (r, target[r["soc_2018_code"]][element])
                for r in subset
                if element in target[r["soc_2018_code"]]
            ]
            denominator = sum(r["employment_2024"] for r, _ in valid)
            value = (
                sum(
                    mean(v for _, v in ratings) * r["employment_2024"]
                    for r, ratings in valid
                )
                / denominator
            )
            output.append(
                {
                    "major_soc": major,
                    "occupation_group": group_name,
                    "skill_id": element,
                    "skill_label": valid[0][1][0][0],
                    "skill_taxonomy": "O*NET",
                    "skill_vintage": "30.3",
                    "employment_reference": weight_source,
                    "importance": value,
                    "scale": "IM 1-5",
                    "covered_soc_count": len(valid),
                    "all_soc_count": len(subset),
                    "covered_employment_jobs": denominator,
                    "employment_coverage": denominator / total if total else None,
                    "status": "synthetic" if demo else "estimated",
                }
            )
    if not output:
        raise ValueError(
            "Skill case requires Essential/Transferable Skills files from O*NET 30.3"
        )
    return output


def market_comparison(rows: list[dict]) -> list[dict]:
    """Common first/latest periods across all series; never compare mismatched months."""
    by_source = defaultdict(dict)
    for row in rows:
        if row["value"] is not None:
            by_source[row["source_id"]][row["period"]] = row
    expected = {s[0] for s in SERIES}
    if set(by_source) != expected:
        raise ValueError("Market comparison needs all six registered series")
    common = sorted(set.intersection(*(set(by_source[s]) for s in expected)))
    if len(common) < 2:
        raise ValueError("Market comparison needs two common nonmissing periods")
    start, end = common[0], common[-1]
    results = []
    for sid, industry, _, metric, unit in SERIES:
        first, last = by_source[sid][start]["value"], by_source[sid][end]["value"]
        results.append(
            {
                "source_id": sid,
                "industry": industry,
                "metric": metric,
                "unit": unit,
                "start_period": start,
                "end_period": end,
                "start_value": first,
                "end_value": last,
                "change_pct": 100 * (last / first - 1) if first else None,
                "common_period_count": len(common),
                "status": "estimated",
            }
        )
    return results


def portfolio_snapshot(
    rows: list[dict], *, demo: bool, build_provenance: dict | None = None
) -> dict:
    occupations = unique_soc(rows)
    provenance = build_provenance or {}
    wage_source = next(
        (s for s in provenance.get("sources", []) if s.get("source_id") == "bls_oews"),
        {},
    )
    generated = provenance.get("generated_at")

    def observation_period(row):
        try:
            return (
                datetime.strptime(str(row.get("wage_vintage", "")), "%B %Y").strftime(
                    "%Y-%m"
                )
                if not demo
                else None
            )
        except ValueError:
            return None

    return {
        "schema_version": SCHEMA,
        "dataset_id": "atlas.occupations.0.6.1",
        "generated_at": generated,
        "geography": "US",
        "unit_of_observation": "SOC2018_occupation",
        "status": "synthetic" if demo else "observed_and_estimated",
        "crosswalk": {
            "source": "O*NET-SOC2019",
            "target": "SOC2018",
            "type": "official; many O*NET children to one SOC; market values deduplicated",
            "multi_target": "crosswalk rows retained in occupations.csv; not summed",
        },
        "records": [
            {
                "canonical_id": f"SOC2018:{r['soc_2018_code']}",
                "source_native_id": r["soc_2018_code"],
                "taxonomy": "SOC",
                "taxonomy_vintage": "2018",
                "title": r["title"],
                "onet_children": r["onet_children"],
                "title_origin": "representative O*NET child; not an official SOC title",
                "onet_titles": r["onet_titles"],
                "source_id": "atlas_demo_fixture" if demo else "bls_oews",
                "source_url": ""
                if demo
                else wage_source.get(
                    "source_url", "https://www.bls.gov/oes/tables.htm"
                ),
                "retrieved_at": None if demo else wage_source.get("retrieved_at"),
                "local_source_modified_at": None
                if demo
                else wage_source.get("local_modified_at"),
                "acquisition_date_status": "synthetic_fixture"
                if demo
                else "recorded"
                if wage_source.get("retrieved_at")
                else "unknown; local file timestamp supplied separately",
                "source_vintage": "deterministic synthetic fixture 0.6.1"
                if demo
                else r.get("wage_vintage"),
                "period": observation_period(r),
                "geography": "US",
                "unit_of_observation": "SOC2018_occupation",
                "currency": "USD",
                "price_year": (observation_period(r) or "")[:4] or None,
                "schema_version": SCHEMA,
                "employment_jobs": r["employment_2024"],
                "median_annual_wage": r["median_annual_wage"],
                "ai_exposure_display": r["ai_exposure"],
                "ai_exposure_source_raw": r["ai_exposure_source_raw"],
                "exposure_status": "synthetic" if demo else "estimated",
                "exposure_source_id": "aioe_2021",
                "exposure_source_url": "https://github.com/AIOE-Data/AIOE",
                "exposure_taxonomy": "SOC2010 to SOC2018 conservative one-to-one bridge",
                "status": "synthetic" if demo else "observed",
                "quality_flags": r.get("data_quality_flags", ""),
            }
            for r in occupations
        ],
        "note": "Local output includes AIOE for downstream analysis. Do not redistribute the occupation-level AIOE layer without verifying its license. Missing values are null, never zero.",
    }


def build_research(raw_dir: Path, processed_dir: Path, research_dir: Path) -> dict:
    rows = read_csv(processed_dir / "occupations.csv")
    manifest = read_json(processed_dir / "data_manifest.json")
    demo = manifest["build"]["mode"] == "demo"
    market = load_market(research_dir)
    bundles: list[dict] = []
    staffing = load_staffing(research_dir)
    skills = skill_composition(
        raw_dir, rows, demo=demo, bundles=bundles, staffing=staffing
    )
    case1 = exposure_case(rows)
    comparison = market_comparison(market)
    result = {
        "schema_version": SCHEMA,
        "version": "0.6.1",
        "mode": "synthetic_occupation_demo" if demo else "public_data",
        "case1": case1,
        "case2": {
            "question": "How do recruitment conditions differ across industries, and which skills distinguish occupation families?",
            "market_comparison": comparison,
            "skills": skills,
            "bundles": bundles,
            "industry_staffing": staffing,
            "note": "Industry skills use published 2025 BLS matrix baseline employment. NAICS 54,55,56 are summed for professional/business services; manufacturing uses 31-33. Only exact SOC keys join to O*NET profiles; suppressed/aggregated unmatched codes remain uncovered. O*NET importance is not posting frequency or an economic complementarity estimate.",
        },
        "market_observations": market,
        "coverage": {
            "onet_occupation_count": len({r["onet_soc_code"] for r in rows}),
            "aioe_occupation_count": len(
                {
                    r["onet_soc_code"]
                    for r in rows
                    if r.get("ai_exposure") not in ("", None)
                }
            ),
            "task_rows": manifest["task_row_count"],
        },
        "aioe_display": manifest["build"]["aioe_display"],
    }
    research_dir.mkdir(parents=True, exist_ok=True)
    write_json(research_dir / "research.json", result)
    write_csv(
        research_dir / "exposure_quartiles.csv",
        case1["quartiles"],
        list(case1["quartiles"][0]),
    )
    write_csv(research_dir / "industry_changes.csv", comparison, list(comparison[0]))
    write_csv(research_dir / "skill_composition.csv", skills, list(skills[0]))
    write_csv(research_dir / "market_observations.csv", market, MARKET_FIELDS)
    write_json(
        research_dir / "portfolio_snapshot.json",
        portfolio_snapshot(rows, demo=demo, build_provenance=manifest),
    )
    (research_dir / "executive-brief.md").write_text(
        executive_brief(result), encoding="utf-8"
    )
    return result


def executive_brief(result: dict) -> str:
    c = result["case1"]
    low, high = c["quartiles"][0], c["quartiles"][-1]
    coverage = result["coverage"]
    lines = [
        "# AI Labor Market Intelligence",
        "",
        "Haojian Dui · Release 0.6.1 · US national public data",
        "",
    ]
    if result["mode"] != "public_data":
        lines += [
            "**DEMO: occupation values and skill ratings are synthetic; industry time series are public observations.**",
            "",
        ]
    lines += [
        "## Decision brief",
        "",
        "Use occupational exposure to choose workflows for evaluation, then use demand and skill evidence to set training priorities.",
        "",
        f"Across {c['sample_soc_count']:,} complete SOC occupations, the highest exposure quartile has an employment-weighted average occupational median wage of ${high['weighted_occupation_median_wage']:,.0f}, compared with ${low['weighted_occupation_median_wage']:,.0f} in the lowest quartile ({c['high_low_wage_ratio']:.2f} times; Table I). This is a wage-level comparison, not an AI wage effect.",
        "",
        f"AIOE covers {coverage['aioe_occupation_count']:,} of {coverage['onet_occupation_count']:,} O*NET occupations ({100 * coverage['aioe_occupation_count'] / coverage['onet_occupation_count']:.1f}%). Unmatched observations remain missing.",
        "",
        "## Table I. Wage and employment by AI exposure quartile",
        "",
        "| Exposure quartile | SOC count | Employment, millions | Weighted occupation median, USD/year |",
        "| --- | ---: | ---: | ---: |",
    ]
    for r in c["quartiles"]:
        lines.append(
            f"| {r['quartile']} | {r['occupation_count']} | {r['employment_jobs'] / 1e6:.2f} | {r['weighted_occupation_median_wage']:,.0f} |"
        )
    lines += [
        "",
        f"Notes: {c['note']} SOCs enter once. Quartiles contain equal numbers of occupations, with code order breaking exposure ties. The sample excludes {c['excluded_soc_count']} SOCs with missing exposure, wage or positive employment.",
        "",
        "## Table II. Industry labor-market change",
        "",
        "| Industry | Measure | First month | Last common month | Change, percent |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for r in result["case2"]["market_comparison"]:
        change = (
            f"{r['change_pct']:+.1f}"
            if r["change_pct"] is not None
            else "Unavailable (zero baseline)"
        )
        lines.append(
            f"| {r['industry']} | {r['metric'].replace('_', ' ')} | {r['start_period']} | {r['end_period']} | {change} |"
        )
    lines += [
        "",
        "Notes: BLS JOLTS openings and CES employment/earnings via FRED; monthly, seasonally adjusted. Endpoints use the same months across all six series. Earnings are nominal; no inflation adjustment is implied. Openings are unfilled positions at month end; payroll employment counts jobs. Source estimates can be revised. CES composition changes can affect average earnings.",
        "",
        "## Table III. Critical Thinking and Active Listening skill bundle",
        "",
        "| Group | Both importance ratings at least 3.5/5, covered employment | Employment coverage |",
        "| --- | ---: | ---: |",
    ]
    for r in result["case2"]["bundles"]:
        if r["share_of_covered_employment"] is not None:
            lines.append(
                f"| {r['occupation_group']} | {100 * r['share_of_covered_employment']:.1f}% | {100 * r['employment_coverage']:.1f}% |"
            )
    lines += [
        "",
        "Notes: O*NET 30.3 IM importance ratings; exact children averaged equally within SOC. National families use OEWS May 2025 employment; industries use the BLS 2025 staffing baseline. Professional/business services sums disjoint NAICS 54,55,56; manufacturing uses 31–33. Industry coverage uses published totals, including unmatched and suppressed cells. Co-occurrence does not establish economic complementarity.",
        "",
        "## Action",
        "",
        "Evaluate a bounded task workflow before purchasing broad training. Pair analytical skills with communication and domain judgment, and validate the relevant occupation's exact ratings in the explorer. Use the scenario tool to compare adoption and training assumptions in hours of capacity; retain headcount as a separate organizational decision.",
        "",
        "## Evidence and reproduction",
        "",
        "`atlas research` regenerates both cases and the structured tables. `atlas market-update` explicitly refreshes six registered public series. `atlas scenario --help` documents the scenario inputs.",
        "",
        "Sources: [BLS OEWS](https://www.bls.gov/oes/tables.htm), [O*NET 30.3](https://www.onetcenter.org/database.html), [AIOE](https://github.com/AIOE-Data/AIOE), [BLS JOLTS via FRED](https://fred.stlouisfed.org/series/JTS540099JOL), [CES via FRED](https://fred.stlouisfed.org/series/USPBS), [BLS industry matrix](https://data.bls.gov/projections/nationalMatrix?queryParams=540000&ioType=i).",
        "",
    ]
    return "\n".join(lines)


def csv_text(rows: list[dict]) -> str:
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return buffer.getvalue()
