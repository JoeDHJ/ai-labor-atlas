from __future__ import annotations

from collections import defaultdict
import math
from statistics import mean


_AGGREGATED_NUMERIC_FIELDS = (
    "ai_exposure",
    "employment_2024",
    "projected_employment_2024_thousands",
    "projected_employment_2034_thousands",
    "employment_change_2024_2034_pct",
    "annual_openings_2024_2034",
    "median_annual_wage",
)
_NON_NEGATIVE_NUMERIC_FIELDS = frozenset(
    {
        "ai_exposure",
        "employment_2024",
        "projected_employment_2024_thousands",
        "projected_employment_2034_thousands",
        "annual_openings_2024_2034",
        "median_annual_wage",
    }
)


def _derived_growth_percent(
    employment_2024: object, employment_2034: object
) -> float | None:
    """Derive an aggregate growth rate from aggregate employment levels.

    Averaging SOC-level percentage changes is not an aggregate employment
    change.  The denominator must be the corresponding aggregated 2024 level.
    """

    start = number(employment_2024, "projected_employment_2024_thousands")
    end = number(employment_2034, "projected_employment_2034_thousands")
    if start is None or end is None or start <= 0:
        return None
    return 100 * (end - start) / start


def number(value, field: str | None = None):
    try:
        parsed = float(value) if value not in (None, "") else None
        if parsed is None or not math.isfinite(parsed):
            return None
        if field in _NON_NEGATIVE_NUMERIC_FIELDS and parsed < 0:
            return None
        if field == "ai_exposure" and parsed > 100:
            return None
        return parsed
    except (TypeError, ValueError):
        return None


def _is_nonfinite(value) -> bool:
    if value in (None, ""):
        return False
    try:
        return not math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def coverage(rows: list[dict[str, str]], field: str) -> float:
    if not rows:
        return 0.0
    return sum(number(row.get(field), field) is not None for row in rows) / len(rows)


def _weighted_mean(
    rows: list[dict[str, str]], value_field: str, weight_field: str
) -> float | None:
    pairs = [
        (
            number(row.get(value_field), value_field),
            number(row.get(weight_field), weight_field),
        )
        for row in rows
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


def aggregate_onet_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """Collapse crosswalk-expanded rows to one auditable record per O*NET code.

    A 2019 O*NET occupation can map to several 2018 SOC codes.  The public
    files do not provide a defensible occupation-specific SOC allocation, so
    the pipeline stores an explicit crosswalk weight and uses a weighted mean
    for reference metrics.  The mapping status and flags remain attached to
    the result so consumers cannot mistake the estimate for a direct SOC
    observation.
    """

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for index, row in enumerate(rows):
        code = str(row.get("onet_soc_code", "")).strip()
        groups[code or f"__missing_onet_{index}"].append(row)

    output: list[dict[str, object]] = []
    for code, members in groups.items():
        base: dict[str, object] = dict(members[0])
        soc_codes = sorted(
            {
                str(member.get("soc_2018_code", "")).strip()
                for member in members
                if str(member.get("soc_2018_code", "")).strip()
            }
        )
        raw_values = [member.get("crosswalk_weight") for member in members]
        raw_weights = []
        missing_weight = False
        for raw_value in raw_values:
            if raw_value in (None, ""):
                missing_weight = True
                raw_weights.append(None)
                continue
            if _is_nonfinite(raw_value):
                raise ValueError("crosswalk_weight must be finite and non-negative")
            try:
                weight = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "crosswalk_weight must be finite and non-negative"
                ) from exc
            if weight < 0:
                raise ValueError("crosswalk_weight must be finite and non-negative")
            raw_weights.append(weight)
        uniform_fallback = len(members) > 1 and missing_weight
        if missing_weight:
            raw_weights = [1.0 / len(members)] * len(members)
        else:
            total_weight = sum(raw_weights)
            if total_weight <= 0:
                raise ValueError("crosswalk_weight must have a positive total")
            raw_weights = [weight / total_weight for weight in raw_weights]

        for field in _AGGREGATED_NUMERIC_FIELDS:
            if field == "employment_change_2024_2034_pct":
                continue
            pairs = [
                (number(member.get(field), field), weight)
                for member, weight in zip(members, raw_weights)
                if number(member.get(field), field) is not None
            ]
            if pairs:
                pair_weight = sum(weight for _, weight in pairs)
                base[field] = sum(value * weight for value, weight in pairs) / pair_weight
            else:
                base[field] = None

        derived_growth = _derived_growth_percent(
            base.get("projected_employment_2024_thousands"),
            base.get("projected_employment_2034_thousands"),
        )
        if derived_growth is not None:
            base["employment_change_2024_2034_pct"] = derived_growth
        else:
            growth_pairs = [
                (number(member.get("employment_change_2024_2034_pct")), weight)
                for member, weight in zip(members, raw_weights)
                if number(member.get("employment_change_2024_2034_pct")) is not None
            ]
            base["employment_change_2024_2034_pct"] = (
                sum(value * weight for value, weight in growth_pairs)
                / sum(weight for _, weight in growth_pairs)
                if growth_pairs
                else None
            )

        flags = {
            flag.strip()
            for member in members
            for flag in str(member.get("data_quality_flags", "")).split(";")
            if flag.strip()
        }
        if len(soc_codes) > 1:
            flags.add("multiple_soc_crosswalk")
            if uniform_fallback:
                flags.add("uniform_crosswalk_fallback")
        if derived_growth is None and len(members) > 1:
            flags.add("growth_rate_weighted_fallback")
        elif not soc_codes:
            flags.add("missing_crosswalk")
        elif len(soc_codes) == 1 and len(members) > 1:
            flags.add("duplicate_crosswalk_rows")
        base.update(
            {
                "onet_soc_code": "" if code.startswith("__missing_onet_") else code,
                "soc_2018_code": ";".join(soc_codes),
                "soc_2018_codes": soc_codes,
                "crosswalk_weight": 1.0,
                "crosswalk_row_count": len(members),
                "mapping_status": (
                    "multiple_soc_crosswalk"
                    if len(soc_codes) > 1
                    else "missing_soc_mapping"
                    if not soc_codes
                    else "single_soc_crosswalk"
                ),
                "aggregation_method": (
                    "crosswalk_weighted_mean"
                    if len(members) > 1
                    else "unmapped_soc_record"
                    if not soc_codes
                    else "direct_soc_record"
                ),
                "data_quality_flags": ";".join(sorted(flags)),
            }
        )
        output.append(base)
    return output


def aggregate_soc_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """Collapse duplicated SOC targets before employment weighting.

    Several O*NET occupations can point to one SOC target. BLS employment is
    an SOC statistic, so it must be counted once for the top-line weighted
    exposure rather than once per O*NET source row.
    """

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for index, row in enumerate(rows):
        code = str(row.get("soc_2018_code", "")).strip()
        groups[code or f"__missing_soc_{index}"].append(row)
    output: list[dict[str, object]] = []
    for code, members in groups.items():
        base: dict[str, object] = dict(members[0])
        flags = {
            flag.strip()
            for member in members
            for flag in str(member.get("data_quality_flags", "")).split(";")
            if flag.strip()
        }
        onet_codes = sorted(
            {
                str(member.get("onet_soc_code", "")).strip()
                for member in members
                if str(member.get("onet_soc_code", "")).strip()
            }
        )
        if len(onet_codes) > 1:
            flags.add("shared_soc_crosswalk")
        for field in _AGGREGATED_NUMERIC_FIELDS:
            if field == "employment_change_2024_2034_pct":
                continue
            values = [
                number(member.get(field), field)
                for member in members
                if number(member.get(field), field) is not None
            ]
            if values:
                base[field] = mean(values)
                if len({round(value, 9) for value in values}) > 1:
                    flags.add("conflicting_soc_duplicates")
            else:
                base[field] = None
        derived_growth = _derived_growth_percent(
            base.get("projected_employment_2024_thousands"),
            base.get("projected_employment_2034_thousands"),
        )
        if derived_growth is not None:
            base["employment_change_2024_2034_pct"] = derived_growth
        else:
            growth_values = [
                number(member.get("employment_change_2024_2034_pct"))
                for member in members
                if number(member.get("employment_change_2024_2034_pct")) is not None
            ]
            base["employment_change_2024_2034_pct"] = (
                mean(growth_values) if growth_values else None
            )
            if len(members) > 1:
                flags.add("growth_rate_mean_fallback")
        base.update(
            {
                "soc_2018_code": "" if code.startswith("__missing_soc_") else code,
                "soc_2018_codes": []
                if code.startswith("__missing_soc_")
                else [code],
                "onet_soc_codes": onet_codes,
                "shared_onet_count": len(onet_codes),
                "data_quality_flags": ";".join(sorted(flags)),
            }
        )
        output.append(base)
    return output


def summarize(rows: list[dict[str, str]]) -> dict[str, object]:
    aggregated_rows = aggregate_onet_rows(rows)
    soc_rows = aggregate_soc_rows(rows)
    mapped_soc_rows = [
        row for row in soc_rows if str(row.get("soc_2018_code", "")).strip()
    ]
    exposures = [number(row.get("ai_exposure"), "ai_exposure") for row in aggregated_rows]
    exposures = [value for value in exposures if value is not None]
    wages = [
        number(row.get("median_annual_wage"), "median_annual_wage")
        for row in aggregated_rows
    ]
    wages = [value for value in wages if value is not None]
    onet_codes = {
        str(row.get("onet_soc_code", "")).strip()
        for row in rows
        if str(row.get("onet_soc_code", "")).strip()
    }
    soc_codes = {
        str(row.get("soc_2018_code", "")).strip()
        for row in rows
        if str(row.get("soc_2018_code", "")).strip()
    }
    onet_row_counts = defaultdict(int)
    for row in rows:
        code = str(row.get("onet_soc_code", "")).strip()
        if code:
            onet_row_counts[code] += 1
    return {
        "rows": len(rows),
        "unique_onet_occupation_count": len(onet_codes),
        "aggregated_onet_occupation_count": len(aggregated_rows),
        "unique_soc_count": len(soc_codes),
        "crosswalk_expanded_row_count": sum(
            count for count in onet_row_counts.values() if count > 1
        ),
        "crosswalk_expanded_onet_count": sum(
            1 for count in onet_row_counts.values() if count > 1
        ),
        "exposure_coverage": coverage(aggregated_rows, "ai_exposure"),
        "wage_coverage": coverage(aggregated_rows, "median_annual_wage"),
        "employment_coverage": coverage(aggregated_rows, "employment_2024"),
        "exposure_mean": mean(exposures) if exposures else None,
        "exposure_min": min(exposures) if exposures else None,
        "exposure_max": max(exposures) if exposures else None,
        "wage_median_mean": mean(wages) if wages else None,
        "employment_weighted_exposure": _weighted_mean(
            mapped_soc_rows, "ai_exposure", "employment_2024"
        ),
        "employment_weighting_unit": "unique_soc_2018",
        "employment_weighting_row_count": len(mapped_soc_rows),
        "employment_weighting_excluded_missing_soc_count": len(soc_rows)
        - len(mapped_soc_rows),
        "shared_soc_count": sum(
            1 for row in soc_rows if row.get("shared_onet_count", 0) > 1
        ),
        "conflicting_soc_count": sum(
            1
            for row in soc_rows
            if "conflicting_soc_duplicates"
            in str(row.get("data_quality_flags", "")).split(";")
        ),
        "multiple_soc_occupation_count": sum(
            1
            for row in aggregated_rows
            if row.get("mapping_status") == "multiple_soc_crosswalk"
        ),
        "aggregation_method": "one_record_per_onet; crosswalk_weighted_mean_for_multiple_soc",
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
) -> list[dict[str, object]]:
    return sorted(
        aggregate_onet_rows(rows),
        key=lambda row: (
            number(row.get(field), field)
            if number(row.get(field), field) is not None
            else float("-inf")
        ),
        reverse=True,
    )
