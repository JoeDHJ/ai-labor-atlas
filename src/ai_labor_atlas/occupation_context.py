"""Conservative occupation suggestions used to connect Career Fit to Atlas."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


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
_ALIAS_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "occupation_aliases_en.json"
)


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


def load_alias_registry(path: Path = _ALIAS_PATH) -> dict[str, dict[str, Any]]:
    """Load the auditable candidate-family crosswalk used for common aliases."""

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
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError("occupation alias candidates must be objects")
            code = str(candidate.get("onet_soc_code", "")).strip()
            note = str(candidate.get("note", "")).strip()
            if not _ONET_CODE.fullmatch(code) or not note:
                raise ValueError(
                    "occupation alias candidates require an O*NET code and note"
                )
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
    alias = _ALIAS_REGISTRY.get(_alias_key(query))
    if alias:
        rows_by_code = {
            str(row.get("onet_soc_code", "")): row for row in rows
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
            "schema_version": "occupation_context.v0.1",
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
    for row in rows:
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
        "schema_version": "occupation_context.v0.1",
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
