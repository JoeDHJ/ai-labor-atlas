from __future__ import annotations

from collections import defaultdict
from statistics import mean


def number(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def coverage(rows: list[dict[str, str]], field: str) -> float:
    if not rows:
        return 0.0
    return sum(number(row.get(field)) is not None for row in rows) / len(rows)


def _weighted_mean(
    rows: list[dict[str, str]], value_field: str, weight_field: str
) -> float | None:
    pairs = [
        (number(row.get(value_field)), number(row.get(weight_field))) for row in rows
    ]
    pairs = [
        (value, weight)
        for value, weight in pairs
        if value is not None and weight is not None and weight >= 0
    ]
    if not pairs or sum(weight for _, weight in pairs) == 0:
        return None
    return sum(value * weight for value, weight in pairs) / sum(
        weight for _, weight in pairs
    )


def summarize(rows: list[dict[str, str]]) -> dict[str, object]:
    exposures = [number(row.get("ai_exposure")) for row in rows]
    exposures = [value for value in exposures if value is not None]
    wages = [number(row.get("median_annual_wage")) for row in rows]
    wages = [value for value in wages if value is not None]
    return {
        "rows": len(rows),
        "exposure_coverage": coverage(rows, "ai_exposure"),
        "wage_coverage": coverage(rows, "median_annual_wage"),
        "employment_coverage": coverage(rows, "employment_2024"),
        "exposure_mean": mean(exposures) if exposures else None,
        "exposure_min": min(exposures) if exposures else None,
        "exposure_max": max(exposures) if exposures else None,
        "wage_median_mean": mean(wages) if wages else None,
        "employment_weighted_exposure": _weighted_mean(
            rows, "ai_exposure", "employment_2024"
        ),
    }


def summarize_tasks(
    rows: list[dict[str, str]], tasks: list[dict[str, str]]
) -> dict[str, object]:
    occupation_codes = {
        row.get("onet_soc_code", "") for row in rows if row.get("onet_soc_code")
    }
    task_codes = {
        task.get("onet_soc_code", "") for task in tasks if task.get("onet_soc_code")
    }
    covered_codes = occupation_codes & task_codes
    return {
        "task_rows": len(tasks),
        "task_occupation_count": len(covered_codes),
        "task_occupation_coverage": (
            len(covered_codes) / len(occupation_codes) if occupation_codes else 0.0
        ),
    }


def group_by_major_soc(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    groups = defaultdict(list)
    for row in rows:
        code = row.get("soc_2018_code", "")
        groups[code[:2] if code else "unknown"].append(row)
    output = []
    for major, members in sorted(groups.items()):
        summary = summarize(members)
        output.append({"soc_major": major, **summary})
    return output


def rank_rows(
    rows: list[dict[str, str]], field: str = "ai_exposure"
) -> list[dict[str, str]]:
    return sorted(
        rows,
        key=lambda row: (
            number(row.get(field))
            if number(row.get(field)) is not None
            else float("-inf")
        ),
        reverse=True,
    )
