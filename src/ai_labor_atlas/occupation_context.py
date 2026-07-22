"""Conservative occupation suggestions used to connect Career Fit to Atlas."""

from __future__ import annotations

import re
from typing import Any


_STOPWORDS = {
    "and",
    " the ",
    "analyst",
    "analysis",
    "associate",
    "manager",
    "senior",
    "specialist",
    "the",
    "of",
    "for",
}


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 2 and token not in _STOPWORDS
    }


def suggest_occupations(
    rows: list[dict[str, Any]], query: str, limit: int = 5
) -> dict[str, Any]:
    """Return reviewable title suggestions; never silently select one."""

    query = query.strip()
    if not query:
        raise ValueError("query is required")
    query_tokens = _tokens(query)
    ranked = []
    for row in rows:
        title = str(row.get("title", ""))
        title_tokens = _tokens(title)
        if not title_tokens or not query_tokens:
            continue
        overlap = query_tokens & title_tokens
        title_lower = title.casefold()
        exact_phrase = query.casefold() in title_lower
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
                    "title_phrase_match" if exact_phrase else "title_token_overlap"
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
            "Suggestions use occupation-title evidence only. Select a standard "
            "occupation before attaching worker comments."
        ),
    }
