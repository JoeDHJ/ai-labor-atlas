"""Run 500 deterministic AI Labor Atlas data and product scenarios.

The audit combines 50 named contract cases with ten controlled variants.  It
checks the measurement layer, crosswalk math, occupation suggestions, public
review contract, market context, and dashboard disclosure without requiring
external data or network access.
"""

from __future__ import annotations

import collections
import json
from pathlib import Path
from typing import Any

from ai_labor_atlas.dashboard import render
from ai_labor_atlas.demo import demo_rows, demo_tasks
from ai_labor_atlas.metrics import (
    aggregate_onet_rows,
    group_by_major_soc,
    rank_rows,
    summarize,
    summarize_tasks,
)
from ai_labor_atlas.occupation_context import build_market_context, suggest_occupations
from ai_labor_atlas.pipeline import _bridge_aioe_to_soc_2018
from ai_labor_atlas.reviews import normalize_review


ROOT = Path(__file__).resolve().parents[1]
VARIANTS = (
    "plain",
    "reverse_rows",
    "whitespace_values",
    "extra_fields",
    "blank_optional_metadata",
    "numeric_types",
    "reordered_tasks",
    "query_casefold",
    "query_padding",
    "safe_public_metadata",
)


def _base_rows() -> list[dict[str, str]]:
    return [{key: str(value) for key, value in row.items()} for row in demo_rows()]


def _row(rows: list[dict[str, str]], index: int = 0) -> dict[str, str]:
    return dict(rows[index])


def _variant_rows(rows: list[dict[str, str]], variant: str) -> list[dict[str, str]]:
    output = [dict(row) for row in rows]
    if variant == "reverse_rows":
        output.reverse()
    elif variant == "whitespace_values":
        output = [{key: f" {value} " for key, value in row.items()} for row in output]
    elif variant == "extra_fields":
        for row in output:
            row["ignored_importer_note"] = "not part of the public contract"
    elif variant == "blank_optional_metadata":
        for row in output:
            for field in ("description", "ai_exposure_source", "data_quality_flags"):
                if field in row:
                    row[field] = ""
    elif variant == "numeric_types":
        for row in output:
            for field in (
                "ai_exposure",
                "employment_2024",
                "median_annual_wage",
                "crosswalk_weight",
            ):
                if field in row and row[field] not in (None, ""):
                    row[field] = float(row[field])
    elif variant == "safe_public_metadata":
        for row in output:
            row["provenance_note"] = "public-source record"
    return output


def _variant_query(query: str, variant: str) -> str:
    if variant == "query_casefold":
        return query.upper()
    if variant == "query_padding":
        return f"  {query}  "
    if variant == "whitespace_values":
        return query.replace(" ", "   ")
    return query


def _variant_tasks(tasks: list[dict[str, str]], variant: str) -> list[dict[str, str]]:
    output = [dict(task) for task in tasks]
    if variant in {"reverse_rows", "reordered_tasks"}:
        output.reverse()
    if variant == "extra_fields":
        for task in output:
            task["ignored_importer_note"] = "not public"
    if variant == "safe_public_metadata":
        output.append(
            {
                "onet_soc_code": "99-9999.00",
                "task_statement": "Unrelated task must not attach to the selected occupation.",
            }
        )
    return output


def _expect_error(fn) -> tuple[bool, str]:
    try:
        fn()
    except ValueError:
        return True, "expected ValueError"
    return False, "expected ValueError was not raised"


def _summary_case(case_id: str, rows: list[dict[str, str]], variant: str) -> tuple[bool, str]:
    rows = _variant_rows(rows, variant)
    if case_id == "summary_empty":
        rows = []
    elif case_id == "summary_missing_numeric":
        rows = [{key: "" for key in rows[0]}]
    elif case_id == "summary_nonfinite_numeric":
        rows = [{**_row(rows), "ai_exposure": "nan", "median_annual_wage": "inf", "employment_2024": "-inf"}]
    elif case_id == "summary_missing_soc_excluded":
        rows = [{**_row(rows), "soc_2018_code": ""}]
    elif case_id == "summary_shared_soc_deduplicated":
        rows = [
            {"onet_soc_code": "A", "soc_2018_code": "15-1252", "ai_exposure": "0.5", "employment_2024": "100"},
            {"onet_soc_code": "B", "soc_2018_code": "15-1252", "ai_exposure": "0.5", "employment_2024": "100"},
            {"onet_soc_code": "C", "soc_2018_code": "15-2051", "ai_exposure": "1.0", "employment_2024": "900"},
        ]
    elif case_id == "summary_duplicate_onet_expansion":
        rows = [_row(rows), _row(rows)]
    elif case_id == "summary_weighted_multiple_soc":
        rows = [
            {**_row(rows), "onet_soc_code": "A", "soc_2018_code": "15-1252", "crosswalk_weight": "0.25", "ai_exposure": "0.2"},
            {**_row(rows), "onet_soc_code": "A", "soc_2018_code": "15-2051", "crosswalk_weight": "0.75", "ai_exposure": "0.8"},
        ]
    elif case_id == "summary_negative_employment_fail_closed":
        rows = [{**_row(rows), "employment_2024": "-10"}]
    elif case_id == "summary_negative_aioe_and_market_metrics":
        rows = [{**_row(rows), "ai_exposure": "-0.2", "median_annual_wage": "-1"}]
    result = summarize(rows)
    checks = {
        "summary_baseline": result["rows"] == 8 and result["exposure_coverage"] > 0.9,
        "summary_empty": result["rows"] == 0 and result["exposure_mean"] is None and result["employment_weighted_exposure"] is None,
        "summary_missing_numeric": result["exposure_coverage"] == 0.0 and result["wage_coverage"] == 0.0 and result["employment_coverage"] == 0.0,
        "summary_nonfinite_numeric": result["exposure_coverage"] == 0.0 and result["wage_coverage"] == 0.0 and result["employment_coverage"] == 0.0,
        "summary_missing_soc_excluded": result["employment_weighting_excluded_missing_soc_count"] == 1 and result["employment_weighted_exposure"] is None,
        "summary_shared_soc_deduplicated": result["shared_soc_count"] == 1 and result["employment_weighting_row_count"] == 2,
        "summary_duplicate_onet_expansion": result["unique_onet_occupation_count"] == 1 and result["crosswalk_expanded_row_count"] == 2,
        "summary_negative_employment_fail_closed": result["employment_coverage"] == 0.0,
        "summary_negative_aioe_and_market_metrics": result["exposure_coverage"] == 0.0 and result["exposure_min"] is None and result["wage_coverage"] == 0.0,
    }
    if case_id == "summary_weighted_multiple_soc":
        expected = abs(aggregate_onet_rows(rows)[0]["ai_exposure"] - 0.65) < 1e-9
    else:
        expected = bool(checks[case_id])
    return bool(expected), json.dumps(result, ensure_ascii=False, default=str)


def _weight_case(case_id: str, rows: list[dict[str, str]], variant: str) -> tuple[bool, str]:
    first = _row(_variant_rows(rows, variant))
    if case_id == "crosswalk_missing_weights_fallback":
        payload = [{**first, "onet_soc_code": "A", "soc_2018_code": "15-1252", "crosswalk_weight": ""}, {**first, "onet_soc_code": "A", "soc_2018_code": "15-2051", "crosswalk_weight": ""}]
        result = aggregate_onet_rows(payload)
        return "uniform_crosswalk_fallback" in result[0]["data_quality_flags"], str(result)
    if case_id == "crosswalk_partial_missing_weights_fallback":
        payload = [{**first, "onet_soc_code": "A", "soc_2018_code": "15-1252", "crosswalk_weight": ""}, {**first, "onet_soc_code": "A", "soc_2018_code": "15-2051", "crosswalk_weight": "0.5"}]
        result = aggregate_onet_rows(payload)
        return "uniform_crosswalk_fallback" in result[0]["data_quality_flags"], str(result)
    if case_id == "crosswalk_explicit_zero_preserved":
        payload = [{**first, "onet_soc_code": "A", "soc_2018_code": "15-1252", "crosswalk_weight": "0", "ai_exposure": "0.1"}, {**first, "onet_soc_code": "A", "soc_2018_code": "15-2051", "crosswalk_weight": "1", "ai_exposure": "0.9"}]
        result = aggregate_onet_rows(payload)
        return abs(result[0]["ai_exposure"] - 0.9) < 1e-9, str(result)
    invalid = {
        "crosswalk_zero_total_rejected": "0",
        "crosswalk_negative_rejected": "-0.1",
        "crosswalk_nan_rejected": "nan",
        "crosswalk_inf_rejected": "inf",
        "crosswalk_negative_inf_rejected": "-inf",
        "crosswalk_text_rejected": "not-number",
    }
    if case_id in invalid:
        return _expect_error(lambda: aggregate_onet_rows([{**first, "onet_soc_code": "A", "soc_2018_code": "15-1252", "crosswalk_weight": invalid[case_id]}]))
    if case_id == "crosswalk_three_weight_normalization":
        payload = [
            {**first, "onet_soc_code": "A", "soc_2018_code": "15-1252", "crosswalk_weight": "0.2", "ai_exposure": "0.1"},
            {**first, "onet_soc_code": "A", "soc_2018_code": "15-2051", "crosswalk_weight": "0.3", "ai_exposure": "0.5"},
            {**first, "onet_soc_code": "A", "soc_2018_code": "15-2052", "crosswalk_weight": "0.5", "ai_exposure": "0.9"},
        ]
        result = aggregate_onet_rows(payload)
        return abs(result[0]["ai_exposure"] - 0.62) < 1e-9, str(result)
    raise AssertionError(f"unknown weight case {case_id}")


def _mapping_case(case_id: str, rows: list[dict[str, str]], variant: str) -> tuple[bool, str]:
    queries = {
        "mapping_data_analyst": "data analyst",
        "mapping_ml_engineer": "ml engineer",
        "mapping_people_analytics": "people analytics analyst",
        "mapping_product_manager": "product manager",
        "mapping_ux_designer": "ux designer",
        "mapping_cybersecurity": "cybersecurity analyst",
        "mapping_hr_business_partner": "hr business partner",
    }
    if case_id in queries:
        result = suggest_occupations(rows, _variant_query(queries[case_id], variant))
        return result["mapping_status"] == "editorial_candidate_crosswalk" and result["requires_confirmation"] is True, str(result)
    if case_id == "mapping_unknown_no_auto_map":
        result = suggest_occupations(rows, _variant_query("Chief Happiness Officer", variant))
        return result["mapping_status"] == "no_reliable_match" and result["requires_confirmation"] is True and not result["candidates"], str(result)
    if case_id == "mapping_empty_query_rejected":
        return _expect_error(lambda: suggest_occupations(rows, " "))
    result = suggest_occupations(rows, _variant_query("Software Developers", variant))
    return result["mapping_status"] == "title_evidence" and bool(result["candidates"]) and all(item["requires_confirmation"] for item in result["candidates"]), str(result)


def _review_case(case_id: str, variant: str) -> tuple[bool, str]:
    base = {
        "review_id": "review-pilot",
        "onet_soc_code": "15-1252.00",
        "source": "user_submitted",
        "review_scope": "occupation",
        "excerpt": "The work combines software design and debugging.",
        "topics": ["tasks_tools"],
    }
    if variant == "safe_public_metadata":
        base.update({"author_display": "Anonymous worker", "review_date": "2025-01-02", "rating": 4})
    if variant in {"whitespace_values", "query_padding"}:
        base["excerpt"] = "  " + base["excerpt"] + "  "
    if case_id == "review_valid_whitelist":
        result = normalize_review({**base, "private_moderation_note": "do not publish"})
        return "private_moderation_note" not in result and result["review_id"] == "review-pilot", str(result)
    invalid = {
        "review_email_rejected": {"excerpt": "Contact person@example.com"},
        "review_phone_rejected": {"excerpt": "Call 555-123-4567"},
        "review_ssn_rejected": {"excerpt": "ID 123-45-6789"},
        "review_bad_date_rejected": {"review_date": "04/03/2025"},
        "review_bad_rating_rejected": {"rating": "6"},
        "review_bad_source_rejected": {"source": "unknown"},
        "review_bad_topic_rejected": {"topics": ["salary_magic"]},
        "review_excerpt_limit_rejected": {"excerpt": "x" * 2001},
        "review_missing_required_rejected": {"review_id": "x"},
    }
    values = invalid[case_id]
    if case_id == "review_missing_required_rejected":
        return _expect_error(lambda: normalize_review(values))
    return _expect_error(lambda: normalize_review({**base, **values}))


def _context_case(case_id: str, rows: list[dict[str, str]], tasks: list[dict[str, str]], variant: str) -> tuple[bool, str]:
    rows = _variant_rows(rows, variant)
    tasks = _variant_tasks(tasks, variant)
    if case_id == "context_baseline":
        result = build_market_context(rows[0], tasks, bridge={"candidates": [{"occupation": rows[1], "structured_similarity": 0.8}]})
        return result["schema_version"] == "market_context.v0.2" and "median_annual_wage" in result["metrics"], str(result)
    if case_id == "context_missing_mapping_disclosed":
        missing = {**rows[0], "soc_2018_code": ""}
        result = build_market_context(missing, [], occupation_rows=[missing])
        return result["mapping"]["status"] == "missing_soc_mapping" and "missing_crosswalk" in result["mapping"]["data_quality_flags"], str(result)
    if case_id == "context_multiple_mapping_disclosed":
        payload = [{**rows[0], "onet_soc_code": "A", "soc_2018_code": "15-1252", "crosswalk_weight": "0.5"}, {**rows[0], "onet_soc_code": "A", "soc_2018_code": "15-2051", "crosswalk_weight": "0.5"}]
        result = build_market_context(payload[0], [], occupation_rows=payload)
        return result["mapping"]["status"] == "multiple_soc_crosswalk" and len(result["mapping"]["soc_2018_codes"]) == 2, str(result)
    if case_id == "context_task_display_capped":
        result = build_market_context(rows[0], tasks * 6)
        return len(result["representative_tasks"]) <= 5, str(result)
    if case_id == "context_unrelated_tasks_excluded":
        result = build_market_context(rows[0], [{**tasks[0], "onet_soc_code": "99-9999.00"}])
        return not result["representative_tasks"], str(result)
    if case_id == "context_invalid_bridge_filtered":
        result = build_market_context(rows[0], [], bridge={"candidates": [{"bad": "candidate"}, {"occupation": rows[1], "structured_similarity": 0.8}]})
        scores, flags, metadata = _bridge_aioe_to_soc_2018(
            {"13-1021": 0.25, "29-2099": 0.5, "29-9099": 0.75},
            {"13-1021", "29-2036", "29-2099", "29-9021", "29-9093", "29-9099"},
        )
        bridge_ok = (
            scores == {"13-1021": 0.25}
            and "aioe_crosswalk_ambiguous" in flags.get("29-2099", set())
            and "aioe_crosswalk_ambiguous" in flags.get("29-9099", set())
            and metadata["source_soc_vintage"] == "2010"
        )
        return len(result["adjacent_occupations"]) == 1 and result["adjacent_occupations"][0]["title"] == rows[1]["title"].strip() and bridge_ok, str(result)
    if case_id == "tasks_empty_coverage_zero":
        result = summarize_tasks(rows, [])
        return result["task_rows"] == 0 and result["task_occupation_coverage"] == 0.0, str(result)
    if case_id == "group_major_soc_summary":
        result = group_by_major_soc(rows)
        return len(result) > 1 and sum(item["rows"] for item in result) == len(rows), str(result)
    if case_id == "rank_missing_value_last":
        result = rank_rows(rows + [{"onet_soc_code": "99-9999.00", "soc_2018_code": "", "title": "Unknown"}])
        return result[-1]["ai_exposure"] is None, str(result)
    page = render(rows, summarize(rows), group_by_major_soc(rows), tasks)
    if variant == "blank_optional_metadata":
        return "DATA QUALITY NOTICE" in page and "provenance is incomplete" in page, f"page length={len(page)}"
    return "DEMO DATASET" in page and "do not use for labor-market decisions" in page, f"page length={len(page)}"


def _base_cases() -> list[tuple[str, str]]:
    return [
        ("summary_baseline", "summary"),
        ("summary_empty", "summary"),
        ("summary_missing_numeric", "summary"),
        ("summary_nonfinite_numeric", "summary"),
        ("summary_missing_soc_excluded", "summary"),
        ("summary_shared_soc_deduplicated", "summary"),
        ("summary_duplicate_onet_expansion", "summary"),
        ("summary_weighted_multiple_soc", "summary"),
        ("summary_negative_employment_fail_closed", "summary"),
        ("summary_negative_aioe_and_market_metrics", "summary"),
        ("crosswalk_missing_weights_fallback", "weight"),
        ("crosswalk_partial_missing_weights_fallback", "weight"),
        ("crosswalk_explicit_zero_preserved", "weight"),
        ("crosswalk_zero_total_rejected", "weight"),
        ("crosswalk_negative_rejected", "weight"),
        ("crosswalk_nan_rejected", "weight"),
        ("crosswalk_inf_rejected", "weight"),
        ("crosswalk_negative_inf_rejected", "weight"),
        ("crosswalk_text_rejected", "weight"),
        ("crosswalk_three_weight_normalization", "weight"),
        ("mapping_data_analyst", "mapping"),
        ("mapping_ml_engineer", "mapping"),
        ("mapping_people_analytics", "mapping"),
        ("mapping_product_manager", "mapping"),
        ("mapping_ux_designer", "mapping"),
        ("mapping_cybersecurity", "mapping"),
        ("mapping_hr_business_partner", "mapping"),
        ("mapping_unknown_no_auto_map", "mapping"),
        ("mapping_empty_query_rejected", "mapping"),
        ("mapping_title_evidence_requires_confirmation", "mapping"),
        ("review_valid_whitelist", "review"),
        ("review_email_rejected", "review"),
        ("review_phone_rejected", "review"),
        ("review_ssn_rejected", "review"),
        ("review_bad_date_rejected", "review"),
        ("review_bad_rating_rejected", "review"),
        ("review_bad_source_rejected", "review"),
        ("review_bad_topic_rejected", "review"),
        ("review_excerpt_limit_rejected", "review"),
        ("review_missing_required_rejected", "review"),
        ("context_baseline", "context"),
        ("context_missing_mapping_disclosed", "context"),
        ("context_multiple_mapping_disclosed", "context"),
        ("context_task_display_capped", "context"),
        ("context_unrelated_tasks_excluded", "context"),
        ("context_invalid_bridge_filtered", "context"),
        ("tasks_empty_coverage_zero", "context"),
        ("group_major_soc_summary", "context"),
        ("rank_missing_value_last", "context"),
        ("dashboard_demo_disclosure", "context"),
    ]


def run() -> dict[str, Any]:
    rows = _base_rows()
    tasks = [{key: str(value) for key, value in row.items()} for row in demo_tasks()]
    all_rows = []
    failures = []
    for case_id, category in _base_cases():
        for variant in VARIANTS:
            try:
                if category == "summary":
                    ok, detail = _summary_case(case_id, rows, variant)
                elif category == "weight":
                    ok, detail = _weight_case(case_id, rows, variant)
                elif category == "mapping":
                    ok, detail = _mapping_case(case_id, rows, variant)
                elif category == "review":
                    ok, detail = _review_case(case_id, variant)
                else:
                    ok, detail = _context_case(case_id, rows, tasks, variant)
            except Exception as exc:  # pragma: no cover - audit output
                ok, detail = False, f"{type(exc).__name__}: {exc}"
            item = {"id": f"{case_id}__{variant}", "base_id": case_id, "category": category, "variant": variant, "ok": bool(ok)}
            all_rows.append(item)
            if not ok:
                failures.append({**item, "detail": detail})
    category_counts = collections.Counter(item["category"] for item in all_rows)
    return {
        "case_count": len(all_rows),
        "base_case_count": len(_base_cases()),
        "variants_per_case": len(VARIANTS),
        "category_counts": dict(category_counts),
        "passed": len(all_rows) - len(failures),
        "failed": len(failures),
        "failures": failures[:30],
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
