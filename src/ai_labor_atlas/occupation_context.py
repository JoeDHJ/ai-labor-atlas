"""Conservative occupation suggestions used to connect Career Fit to Atlas."""

from __future__ import annotations

import re
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
                "requires_confirmation": True,
            }
        )
    ranked.sort(key=lambda item: (-item["match_score"], item["title"]))
    return {
        "schema_version": "occupation_context.v0.1",
        "query": query,
        "candidates": ranked[: max(0, limit)],
        "requires_confirmation": True,
        "interpretation": (
            "Suggestions use normalized occupation-title evidence and compatible "
            "role terms only. Select a standard occupation before attaching worker "
            "comments; an empty list means the title evidence is not strong enough."
        ),
    }
