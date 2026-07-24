"""Transparent, source-preserving worker-review context.

Reviews are intentionally kept separate from the measurement layer.  This
module validates a small, auditable import contract and never turns comments
into an overall occupation score.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from typing import Any


REVIEW_SCHEMA_VERSION = "occupation_reviews.v0.1"
REVIEW_DISCLOSURE = (
    "Reviews are user-generated and may be incomplete, subjective, outdated, "
    "or biased. They are not verified facts or representative of all workers. "
    "Source links and dates are shown where available."
)
SOURCE_LABELS = {
    "user_submitted": "User submitted",
    "reddit": "Reddit",
    "indeed": "Indeed",
    "other": "Other public source",
}
SCOPE_LABELS = {
    "occupation": "Occupation context",
    "employer_role": "Employer and role",
    "job_posting": "Specific job posting",
}
TOPIC_LABELS = {
    "pay_benefits": "Pay and benefits",
    "interview_management": "Interview and management",
    "work_environment": "Work environment",
    "workload": "Workload",
    "growth": "Growth",
    "tasks_tools": "Tasks and tools",
    "other": "Other",
}
_DATE_FIELDS = ("review_date", "date", "created_at")
_ONET_CODE = re.compile(r"^\d{2}-\d{4}\.\d{2}$")
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-])\d{3}[\s.-]\d{4}(?!\d)"
)
_US_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
MAX_EXCERPT_LENGTH = 2_000
MAX_VALIDATION_ERRORS = 50


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _review_date(row: dict[str, Any]) -> str:
    for field in _DATE_FIELDS:
        value = _text(row.get(field))
        if value:
            try:
                date.fromisoformat(value[:10])
            except ValueError as exc:
                raise ValueError(f"review date must use YYYY-MM-DD: {value}") from exc
            return value[:10]
    return ""


def _source_url(value: Any) -> str:
    url = _text(value)
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must be an http(s) URL")
    _reject_common_pii("source_url", url)
    return url


def _reject_common_pii(field: str, value: str) -> None:
    if _EMAIL.search(value) or _PHONE.search(value) or _US_SSN.search(value):
        raise ValueError(
            f"{field} must not contain an email address, phone number, or government ID"
        )


def normalize_review(row: dict[str, Any]) -> dict[str, Any]:
    """Return the public review fields after strict validation.

    The whitelist is deliberate: importer-specific fields, contact details,
    and hidden moderation notes never reach the public dashboard.
    """

    if not isinstance(row, dict):
        raise ValueError("each review must be a JSON object")
    review_id = _text(row.get("review_id"))
    occupation_code = _text(row.get("onet_soc_code"))
    excerpt = _text(row.get("excerpt") or row.get("text"))
    if not review_id or not occupation_code or not excerpt:
        raise ValueError("review_id, onet_soc_code, and excerpt are required")
    if not _ONET_CODE.fullmatch(occupation_code):
        raise ValueError("onet_soc_code must use the O*NET format NN-NNNN.NN")
    if len(review_id) > 200:
        raise ValueError("review_id is too long")
    if len(excerpt) > MAX_EXCERPT_LENGTH:
        raise ValueError(f"excerpt must be at most {MAX_EXCERPT_LENGTH} characters")
    for field in ("author_display", "employer", "job_title", "location"):
        value = _text(row.get(field))
        if len(value) > 200:
            raise ValueError(f"{field} is too long")
        _reject_common_pii(field, value)
    _reject_common_pii("excerpt", excerpt)
    source = _text(row.get("source")).casefold() or "other"
    if source not in SOURCE_LABELS:
        raise ValueError(f"unsupported review source: {source}")
    scope = _text(row.get("review_scope")).casefold() or "occupation"
    if scope not in SCOPE_LABELS:
        raise ValueError(f"unsupported review scope: {scope}")
    topics = row.get("topics", [])
    if isinstance(topics, str):
        topics = [item.strip() for item in topics.split(",") if item.strip()]
    if not isinstance(topics, list):
        raise ValueError("topics must be a list or comma-separated string")
    normalized_topics = []
    for topic in topics:
        key = _text(topic).casefold()
        if key not in TOPIC_LABELS:
            raise ValueError(f"unsupported review topic: {key}")
        if key not in normalized_topics:
            normalized_topics.append(key)
    rating = row.get("rating")
    if rating in (None, ""):
        normalized_rating = None
    else:
        try:
            normalized_rating = float(rating)
        except (TypeError, ValueError) as exc:
            raise ValueError("rating must be a number from 1 to 5") from exc
        if not 1 <= normalized_rating <= 5:
            raise ValueError("rating must be a number from 1 to 5")
        if normalized_rating.is_integer():
            normalized_rating = int(normalized_rating)
    return {
        "review_id": review_id,
        "onet_soc_code": occupation_code,
        "source": source,
        "source_url": _source_url(row.get("source_url")),
        "review_scope": scope,
        "review_date": _review_date(row),
        "author_display": _text(row.get("author_display")),
        "employer": _text(row.get("employer")),
        "job_title": _text(row.get("job_title")),
        "location": _text(row.get("location")),
        "topics": normalized_topics,
        "rating": normalized_rating,
        "excerpt": excerpt,
    }


def _read_review_rows(path: Path) -> tuple[list[Any] | None, str | None]:
    """Read the file envelope without weakening row-level validation."""

    if not path.exists():
        return [], None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"invalid review JSON in {path}: {exc.msg}"
    rows = payload.get("reviews") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return None, f"{path} must contain a JSON list or a reviews list"
    return rows, None


def _validation_field(message: str) -> str:
    """Map a normalization message to the field a maintainer should fix."""

    for field in (
        "review_id",
        "onet_soc_code",
        "excerpt",
        "source_url",
        "author_display",
        "employer",
        "job_title",
        "location",
        "review_date",
        "topics",
        "rating",
    ):
        if message.startswith(field):
            return field
    if message.startswith("unsupported review source"):
        return "source"
    if message.startswith("unsupported review scope"):
        return "review_scope"
    if message.startswith("unsupported review topic"):
        return "topics"
    return "review"


def _validate_rows(rows: list[Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate every row and return a public diagnostic plus normalized rows."""

    errors: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    row_numbers: list[int] = []
    for row_number, row in enumerate(rows, start=1):
        try:
            normalized.append(normalize_review(row))
            row_numbers.append(row_number)
        except ValueError as exc:
            errors.append(
                {
                    "row": row_number,
                    "field": _validation_field(str(exc)),
                    "message": str(exc),
                }
            )

    id_locations: defaultdict[str, list[int]] = defaultdict(list)
    for row_number, review in zip(row_numbers, normalized):
        id_locations[review["review_id"]].append(row_number)
    duplicate_ids = sorted(
        review_id
        for review_id, locations in id_locations.items()
        if len(locations) > 1
    )
    for review_id in duplicate_ids:
        for row_number in id_locations[review_id]:
            errors.append(
                {
                    "row": row_number,
                    "field": "review_id",
                    "message": (
                        "review_id values must be unique within the import: "
                        f"{review_id}"
                    ),
                }
            )

    source_counts = Counter(review["source"] for review in normalized)
    topic_counts = Counter(
        topic for review in normalized for topic in review["topics"]
    )
    occupation_codes = sorted(
        {review["onet_soc_code"] for review in normalized}
    )
    errors.sort(key=lambda item: (item["row"], item["field"]))
    invalid_rows = {item["row"] for item in errors}
    report = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "valid": not errors,
        "row_count": len(rows),
        "normalized_row_count": len(normalized),
        "invalid_row_count": len(invalid_rows),
        "duplicate_review_ids": duplicate_ids,
        "occupation_count": len(occupation_codes),
        "occupation_codes": occupation_codes,
        "source_counts": dict(sorted(source_counts.items())),
        "topic_counts": dict(sorted(topic_counts.items())),
        "error_count": len(errors),
        "errors": errors[:MAX_VALIDATION_ERRORS],
        "errors_truncated": len(errors) > MAX_VALIDATION_ERRORS,
    }
    return report, normalized


def validate_review_file(path: Path) -> dict[str, Any]:
    """Return an actionable report without exposing review text or private fields."""

    rows, file_error = _read_review_rows(path)
    report: dict[str, Any] = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "input": str(path),
        "present": path.exists(),
    }
    if file_error:
        report.update(
            {
                "valid": False,
                "row_count": 0,
                "normalized_row_count": 0,
                "invalid_row_count": 0,
                "duplicate_review_ids": [],
                "occupation_count": 0,
                "occupation_codes": [],
                "source_counts": {},
                "topic_counts": {},
                "error_count": 1,
                "errors": [{"row": None, "field": "file", "message": file_error}],
                "errors_truncated": False,
                "note": "Fix the file envelope before publishing this import.",
            }
        )
        return report

    validation, _ = _validate_rows(rows or [])
    report.update(validation)
    report["note"] = (
        "Ready for strict dashboard import."
        if report["valid"]
        else "Fix every reported error before publishing this import."
    )
    if not report["present"]:
        report["note"] = (
            "No review import found. The dashboard will show no public worker comments."
        )
    return report


def load_reviews(path: Path) -> list[dict[str, Any]]:
    """Load a local review import; a missing file means no reviews are loaded."""

    rows, file_error = _read_review_rows(path)
    if file_error:
        raise ValueError(file_error)
    report, normalized = _validate_rows(rows or [])
    if not report["valid"]:
        raise ValueError(report["errors"][0]["message"])
    return normalized


def summarize_reviews(
    reviews: list[dict[str, Any]], occupation_code: str, limit: int = 20
) -> dict[str, Any]:
    """Create the public occupation context without a sentiment or truth score."""

    safe_reviews: list[dict[str, Any]] = []
    for review in reviews:
        try:
            safe_reviews.append(normalize_review(review))
        except (TypeError, ValueError):
            continue
    all_items = [
        review
        for review in safe_reviews
        if review.get("onet_soc_code") == occupation_code
    ]
    all_items.sort(key=lambda review: review.get("review_date", ""), reverse=True)
    items = all_items[: max(0, limit)]
    topic_counts = Counter(
        topic for review in items for topic in review.get("topics", [])
    )
    source_counts = Counter(review.get("source", "other") for review in items)
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "occupation_code": occupation_code,
        "available": bool(items),
        "review_count": len(items),
        "total_review_count": len(all_items),
        "display_limit": max(0, limit),
        "is_truncated": len(all_items) > len(items),
        "source_counts": dict(sorted(source_counts.items())),
        "topic_counts": dict(sorted(topic_counts.items())),
        "source_labels": SOURCE_LABELS.copy(),
        "topic_labels": TOPIC_LABELS.copy(),
        "reviews": items,
        "disclosure": REVIEW_DISCLOSURE,
        "interpretation": (
            "These comments provide context for questions about work experience. "
            "They are not an occupation rating and do not change Atlas measures."
        ),
    }


def public_review_labels() -> dict[str, dict[str, str]]:
    """Expose labels for clients that render the contract outside the dashboard."""

    return {
        "sources": SOURCE_LABELS.copy(),
        "scopes": SCOPE_LABELS.copy(),
        "topics": TOPIC_LABELS.copy(),
    }
