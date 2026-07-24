"""Conservative occupation suggestions used to connect Career Fit to Atlas."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .metrics import aggregate_onet_rows
from .runtime import config_path


_STOPWORDS = {
    "and",
    "analysis",
    "associate",
    "entry",
    "for",
    "junior",
    "lead",
    "of",
    "senior",
    "the",
}
_ROLE_TOKENS = {
    "administrator",
    "analyst",
    "architect",
    "auditor",
    "coordinator",
    "consultant",
    "designer",
    "developer",
    "director",
    "economist",
    "engineer",
    "manager",
    "operator",
    "planner",
    "researcher",
    "scientist",
    "specialist",
    "technician",
}
_ONET_CODE = re.compile(r"^\d{2}-\d{4}\.\d{2}$")
def _normalize_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        return token[:-1]
    return token


def _token_sequence(value: str) -> list[str]:
    return [
        _normalize_token(token)
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 2 and token not in _STOPWORDS
    ]


def _alias_key(value: str) -> str:
    return " ".join(
        _normalize_token(token)
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 1 and token not in _STOPWORDS
    )


def load_alias_registry(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load the auditable candidate-family crosswalk used for common aliases."""

    path = path or config_path("occupation_aliases_en.json")
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid occupation alias JSON in {path}: {exc.msg}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
        raise ValueError(f"{path} must contain an entries list")
    registry: dict[str, dict[str, Any]] = {}
    for entry in payload["entries"]:
        if not isinstance(entry, dict):
            raise ValueError("each occupation alias entry must be an object")
        aliases = entry.get("aliases")
        candidates = entry.get("candidates")
        if (
            not isinstance(aliases, list)
            or not aliases
            or not isinstance(candidates, list)
            or not candidates
        ):
            raise ValueError("occupation alias entries require aliases and candidates")
        normalized_candidates = []
        seen_candidate_codes: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError("occupation alias candidates must be objects")
            code = str(candidate.get("onet_soc_code", "")).strip()
            note = str(candidate.get("note", "")).strip()
            if not _ONET_CODE.fullmatch(code) or not note:
                raise ValueError(
                    "occupation alias candidates require an O*NET code and note"
                )
            if code in seen_candidate_codes:
                raise ValueError(
                    f"duplicate O*NET candidate code {code} in occupation alias entry"
                )
            seen_candidate_codes.add(code)
            normalized_candidates.append(
                {"onet_soc_code": code, "note": note}
            )
        normalized_entry = {
            "label": str(entry.get("label", "")).strip(),
            "note": str(entry.get("note", "")).strip(),
            "candidates": normalized_candidates,
        }
        if not normalized_entry["label"] or not normalized_entry["note"]:
            raise ValueError("occupation alias entries require label and note")
        for alias in aliases:
            key = _alias_key(str(alias))
            if not key:
                raise ValueError("occupation alias values cannot be empty")
            if key in registry:
                raise ValueError(f"duplicate occupation alias: {alias}")
            registry[key] = {"alias": str(alias).strip(), **normalized_entry}
    return registry


def validate_alias_registry(
    registry: dict[str, dict[str, Any]], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Fail closed when an alias points outside the current Atlas release."""

    release_codes = {
        str(row.get("onet_soc_code", "")).strip()
        for row in rows
        if str(row.get("onet_soc_code", "")).strip()
    }
    candidate_codes = {
        item["onet_soc_code"]
        for entry in registry.values()
        for item in entry["candidates"]
    }
    missing_codes = sorted(candidate_codes - release_codes)
    if missing_codes:
        joined = ", ".join(missing_codes)
        raise ValueError(
            "occupation alias registry references O*NET codes missing from the "
            f"current Atlas release: {joined}"
        )
    return {
        "valid": True,
        "alias_count": len(registry),
        "candidate_code_count": len(candidate_codes),
    }


_ALIAS_REGISTRY = load_alias_registry()


def _tokens(value: str) -> set[str]:
    return set(_token_sequence(value))


def _contains_phrase(query_tokens: list[str], title_tokens: list[str]) -> bool:
    width = len(query_tokens)
    return bool(
        width
        and any(
            title_tokens[index : index + width] == query_tokens
            for index in range(len(title_tokens) - width + 1)
        )
    )


def _role_compatible(query_tokens: set[str], title_tokens: set[str]) -> bool:
    query_roles = query_tokens & _ROLE_TOKENS
    query_specific = query_tokens - _ROLE_TOKENS
    title_roles = title_tokens & _ROLE_TOKENS
    if not query_specific:
        return False
    if not query_roles and len(query_specific) < 2:
        return False
    if not query_specific.issubset(title_tokens):
        return False
    if query_roles and not query_roles & title_roles:
        return False
    return True


def suggest_occupations(
    rows: list[dict[str, Any]], query: str, limit: int = 5
) -> dict[str, Any]:
    """Return reviewable title suggestions; never silently select one."""

    query = query.strip()
    if not query:
        raise ValueError("query is required")
    candidate_rows = aggregate_onet_rows(rows)
    alias = _ALIAS_REGISTRY.get(_alias_key(query))
    if alias:
        rows_by_code = {
            str(row.get("onet_soc_code", "")): row for row in candidate_rows
        }
        candidates = []
        for item in alias["candidates"]:
            row = rows_by_code.get(item["onet_soc_code"])
            if row is None:
                continue
            candidates.append(
                {
                    "onet_soc_code": item["onet_soc_code"],
                    "title": row.get("title", ""),
                    "soc_2018_code": row.get("soc_2018_code", ""),
                    "match_score": None,
                    "basis": ["editorial_alias_candidate"],
                    "mapping_status": "candidate_family",
                    "mapping_note": item["note"],
                    "requires_confirmation": True,
                }
            )
        return {
            "schema_version": "occupation_context.v0.3",
            "query": query,
            "candidates": candidates[: max(0, limit)],
            "requires_confirmation": True,
            "mapping_status": "editorial_candidate_crosswalk",
            "mapping_label": alias["label"],
            "mapping_note": alias["note"],
            "interpretation": (
                "These are curated candidate occupation families, not an automatic "
                "mapping. Confirm one from the job tasks before attaching worker comments."
            ),
        }
    query_sequence = _token_sequence(query)
    query_tokens = set(query_sequence)
    ranked = []
    for row in candidate_rows:
        title = str(row.get("title", ""))
        title_sequence = _token_sequence(title)
        title_tokens = set(title_sequence)
        if not title_tokens or not query_tokens:
            continue
        if not _role_compatible(query_tokens, title_tokens):
            continue
        overlap = query_tokens & title_tokens
        exact_phrase = _contains_phrase(query_sequence, title_sequence)
        score = (1.0 if exact_phrase else 0.0) + len(overlap) / max(
            len(query_tokens), 1
        )
        if score <= 0:
            continue
        ranked.append(
            {
                "onet_soc_code": row.get("onet_soc_code", ""),
                "title": title,
                "soc_2018_code": row.get("soc_2018_code", ""),
                "match_score": round(min(score / 2, 1.0), 3),
                "basis": [
                    "title_phrase_match"
                    if exact_phrase
                    else "role_compatible_title_overlap"
                ],
                "mapping_status": "title_evidence",
                "requires_confirmation": True,
            }
        )
    ranked.sort(key=lambda item: (-item["match_score"], item["title"]))
    return {
        "schema_version": "occupation_context.v0.3",
        "query": query,
        "candidates": ranked[: max(0, limit)],
        "requires_confirmation": True,
        "mapping_status": "title_evidence" if ranked else "no_reliable_match",
        "interpretation": (
            "Suggestions use normalized occupation-title evidence and compatible "
            "role terms only. Select a standard occupation before attaching worker "
            "comments; an empty list means the title evidence is not strong enough."
        ),
    }


def build_market_context(
    occupation: dict[str, Any],
    tasks: list[dict[str, Any]],
    bridge: dict[str, Any] | None = None,
    occupation_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Expose a provenance-preserving market snapshot for one O*NET occupation.

    ``occupation_rows`` should contain every crosswalk row for the selected
    O*NET code.  When several SOC targets exist, the metrics are explicitly
    crosswalk-weighted and the mapping warning is carried to the consumer.
    """

    source_rows = occupation_rows or [occupation]
    aggregated = aggregate_onet_rows(source_rows)
    selected = aggregated[0] if aggregated else dict(occupation)
    code = str(selected.get("onet_soc_code") or occupation.get("onet_soc_code", ""))
    task_rows = [
        {
            "task_statement": str(row.get("task_statement", "")),
            "task_type": str(row.get("task_type", "")),
            "task_date": str(row.get("task_date", "")),
        }
        for row in tasks
        if str(row.get("onet_soc_code", "")) == code
        and str(row.get("task_statement", "")).strip()
    ][:5]
    alternatives = []
    bridge_candidates = bridge.get("candidates", []) if isinstance(bridge, dict) else []
    for candidate in bridge_candidates[:5]:
        if not isinstance(candidate, dict):
            continue
        candidate_occupation = candidate.get("occupation")
        if not isinstance(candidate_occupation, dict):
            candidate_occupation = {}
        candidate_code = str(
            candidate.get("onet_soc_code") or candidate_occupation.get("onet_soc_code", "")
        ).strip()
        candidate_title = str(
            candidate.get("title") or candidate_occupation.get("title", "")
        ).strip()
        if not candidate_code or not candidate_title:
            continue
        alternatives.append(
            {
                "onet_soc_code": candidate_code,
                "title": candidate_title,
                "structured_similarity": candidate.get("structured_similarity"),
                "software_overlap": candidate.get("software_overlap"),
                "task_similarity": candidate.get("task_similarity"),
                "confidence": candidate.get("confidence"),
                "labor_market": {
                    "median_annual_wage": candidate_occupation.get("median_annual_wage"),
                    "annual_openings_2024_2034": candidate_occupation.get(
                        "annual_openings_2024_2034"
                    ),
                    "employment_change_2024_2034_pct": candidate_occupation.get(
                        "employment_change_2024_2034_pct"
                    ),
                },
                "training_hint": candidate.get("training_hint", ""),
            }
        )
    soc_codes = selected.get("soc_2018_codes", [])
    if not isinstance(soc_codes, list):
        soc_codes = [
            value.strip()
            for value in str(selected.get("soc_2018_code", "")).split(";")
            if value.strip()
        ]
    mapping_status = str(selected.get("mapping_status", "single_soc_crosswalk"))
    row_count = int(selected.get("crosswalk_row_count") or len(source_rows) or 1)
    quality_flags = [
        flag.strip()
        for flag in str(selected.get("data_quality_flags", "")).split(";")
        if flag.strip()
    ]
    weighting_note = (
        "no SOC mapping is available"
        if "missing_crosswalk" in quality_flags
        else "uniform fallback; no source crosswalk allocation was available"
        if "uniform_crosswalk_fallback" in quality_flags
        else "explicit crosswalk weights"
    )
    return {
        "schema_version": "market_context.v0.2",
        "occupation_code": code,
        "title": selected.get("title", occupation.get("title", "")),
        "metrics": {
            "median_annual_wage": selected.get("median_annual_wage"),
            "employment_2024": selected.get("employment_2024"),
            "annual_openings_2024_2034": selected.get("annual_openings_2024_2034"),
            "employment_change_2024_2034_pct": selected.get(
                "employment_change_2024_2034_pct"
            ),
            "ai_exposure": selected.get("ai_exposure"),
            "ai_exposure_display": {
                "scale": "0-100 relative display scale",
                "interpretation": (
                    "Higher means relatively higher AIOE within this release. "
                    "It is not a probability, replacement risk, or forecast of job loss."
                ),
            },
        },
        "provenance": {
            "onet_version": selected.get("onet_version"),
            "wage_vintage": selected.get("wage_vintage"),
            "projection_vintage": selected.get("projection_vintage"),
            "ai_exposure_source": selected.get("ai_exposure_source"),
            "ai_exposure_soc_vintage": selected.get("ai_exposure_soc_vintage"),
            "crosswalk_method": selected.get("crosswalk_method"),
            "data_quality_flags": selected.get("data_quality_flags", ""),
        },
        "mapping": {
            "status": mapping_status,
            "onet_soc_code": code,
            "soc_2018_codes": soc_codes,
            "row_count": row_count,
            "aggregation_method": selected.get(
                "aggregation_method", "direct_soc_record"
            ),
            "crosswalk_weighting": weighting_note,
            "data_quality_flags": quality_flags,
        },
        "representative_tasks": task_rows,
        "adjacent_occupations": alternatives,
        "interpretation": (
            "These are descriptive market and task signals. AI exposure is a 0-100 relative display, not a job-loss probability, "
            "wage differences are not causal, adjacent occupations are not personal recommendations, "
            "and multiple SOC mappings are weighted reference estimates rather than a direct occupation statistic."
        ),
    }
