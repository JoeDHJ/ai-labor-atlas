from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path


DOMAIN_WEIGHTS = {
    "essential": 0.22,
    "transferable": 0.24,
    "knowledge": 0.18,
    "abilities": 0.18,
    "activities": 0.18,
}
DOMAIN_FILES = {
    "essential": "Essential Skills.txt",
    "transferable": "Transferable Skills.txt",
    "knowledge": "Knowledge.txt",
    "abilities": "Abilities.txt",
    "activities": "Work Activities.txt",
}
TASK_STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "assist",
    "based",
    "been",
    "between",
    "can",
    "carry",
    "complete",
    "coordinate",
    "could",
    "create",
    "data",
    "develop",
    "different",
    "during",
    "each",
    "ensure",
    "for",
    "from",
    "general",
    "have",
    "into",
    "maintain",
    "manage",
    "may",
    "more",
    "other",
    "perform",
    "provide",
    "related",
    "report",
    "review",
    "should",
    "some",
    "such",
    "support",
    "task",
    "that",
    "the",
    "their",
    "these",
    "this",
    "through",
    "to",
    "use",
    "using",
    "with",
    "work",
}
TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


def _number(value: object, *, non_negative: bool = False) -> float | None:
    try:
        parsed = float(value) if value not in (None, "") else None
        if parsed is None or not math.isfinite(parsed):
            return None
        return None if non_negative and parsed < 0 else parsed
    except (TypeError, ValueError):
        return None


def _base_code(code: str) -> str:
    return str(code).split(".", 1)[0]


def _find_text_root(raw_dir: Path) -> Path | None:
    likely = [
        raw_dir / "onet_30_3_text_inspect" / "db_30_3_text",
        raw_dir / "onet_30_3_text",
        raw_dir,
    ]
    for path in likely:
        if (path / "Essential Skills.txt").exists():
            return path
    matches = list(raw_dir.rglob("Essential Skills.txt")) if raw_dir.exists() else []
    return matches[0].parent if matches else None


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in TOKEN_RE.findall(value.casefold())
        if token not in TASK_STOPWORDS
    }


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _snapshot(row: dict[str, str], profile_source: str = "") -> dict[str, object]:
    exposure = _number(row.get("ai_exposure"))
    return {
        "onet_soc_code": row.get("onet_soc_code", ""),
        "title": row.get("title", ""),
        "soc_2018_code": row.get("soc_2018_code", ""),
        # The public dataset exposes AIOE as a 0--100 relative display scale,
        # not its signed standardized source value.
        "ai_exposure": exposure if exposure is not None and 0 <= exposure <= 100 else None,
        "median_annual_wage": _number(
            row.get("median_annual_wage"), non_negative=True
        ),
        "employment_2024": _number(row.get("employment_2024"), non_negative=True),
        "employment_change_2024_2034_pct": _number(
            row.get("employment_change_2024_2034_pct")
        ),
        "annual_openings_2024_2034": _number(
            row.get("annual_openings_2024_2034"), non_negative=True
        ),
        "profile_source": profile_source,
    }


class OccupationBridge:
    """Explainable occupation-to-occupation bridge calculations.

    Structured O*NET ratings are the primary distance signal. Software overlap
    and task-text overlap are returned as separate evidence, so a user can see
    why two occupations are close without treating text similarity as a worker
    ability estimate. Detailed O*NET variants can supply a family-average
    fallback for a parent code such as Data Scientists; that provenance lowers
    the confidence label rather than being hidden.
    """

    def __init__(
        self,
        raw_dir: Path,
        occupation_rows: list[dict[str, str]],
        task_rows: list[dict[str, str]],
    ) -> None:
        self.raw_dir = raw_dir
        self.rows_by_code = {
            row.get("onet_soc_code", ""): row
            for row in occupation_rows
            if row.get("onet_soc_code")
        }
        self.tasks_by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
        for task in task_rows:
            code = task.get("onet_soc_code", "")
            if code:
                self.tasks_by_code[code].append(task)
        self.profiles: dict[str, dict[str, float]] = {}
        self.profile_source: dict[str, str] = {}
        self.software: dict[str, set[str]] = defaultdict(set)
        self.task_tokens: dict[str, set[str]] = {}
        self.task_token_rows: dict[str, list[tuple[str, set[str]]]] = {}
        self.bounds: dict[str, tuple[float, float]] = {}
        self.available = False
        self._cache: dict[tuple[str, int], dict[str, object]] = {}
        self._load_structured_profiles()
        self._build_task_profiles()

    def _load_structured_profiles(self) -> None:
        text_root = _find_text_root(self.raw_dir)
        if not text_root:
            return
        exact: dict[str, dict[str, float]] = defaultdict(dict)
        family: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for domain, filename in DOMAIN_FILES.items():
            path = text_root / filename
            if not path.exists():
                continue
            for row in _read_tsv(path):
                if row.get("Scale ID") != "IM":
                    continue
                value = _number(row.get("Data Value"))
                code = row.get("O*NET-SOC Code", "")
                element = row.get("Element ID", "")
                if value is None or not code or not element:
                    continue
                key = f"{domain}:{element}"
                exact[code][key] = value
                family[_base_code(code)][key].append(value)

        for code in self.rows_by_code:
            if exact.get(code):
                self.profiles[code] = dict(exact[code])
                self.profile_source[code] = "exact"
                continue
            family_values = family.get(_base_code(code), {})
            if family_values:
                self.profiles[code] = {
                    key: sum(values) / len(values)
                    for key, values in family_values.items()
                    if values
                }
                self.profile_source[code] = "family_average"
        all_values: dict[str, list[float]] = defaultdict(list)
        for profile in self.profiles.values():
            for key, value in profile.items():
                all_values[key].append(value)
        self.bounds = {
            key: (min(values), max(values))
            for key, values in all_values.items()
            if values
        }
        software_path = text_root / "Software Skills.txt"
        if software_path.exists():
            with software_path.open(
                newline="", encoding="utf-8-sig", errors="replace"
            ) as handle:
                for row in csv.DictReader(handle, delimiter="\t"):
                    code = row.get("O*NET-SOC Code", "")
                    name = row.get("Workplace Example", "").strip().casefold()
                    if code and name:
                        self.software[code].add(name)
        for code in self.rows_by_code:
            if not self.software.get(code):
                family_values = set()
                for source_code, values in self.software.items():
                    if _base_code(source_code) == _base_code(code):
                        family_values.update(values)
                if family_values:
                    self.software[code] = family_values
        self.available = bool(self.profiles)

    def _build_task_profiles(self) -> None:
        for code, tasks in self.tasks_by_code.items():
            preferred = [task for task in tasks if task.get("task_type") == "Core"]
            selected = preferred or tasks
            rows = [
                (
                    task.get("task_statement", ""),
                    _tokens(task.get("task_statement", "")),
                )
                for task in selected
            ]
            rows = [(statement, tokens) for statement, tokens in rows if tokens]
            self.task_token_rows[code] = rows
            combined: set[str] = set()
            for _, tokens in rows:
                combined.update(tokens)
            self.task_tokens[code] = combined

    def _normalized(self, profile: dict[str, float], key: str) -> float:
        value = profile.get(key)
        if value is None:
            return 0.0
        lower, upper = self.bounds.get(key, (value, value))
        return (value - lower) / (upper - lower) if upper > lower else 0.0

    def _structural_distance(
        self, source_code: str, target_code: str
    ) -> tuple[float, dict[str, float], int]:
        source = self.profiles[source_code]
        target = self.profiles[target_code]
        distances: dict[str, float] = {}
        for domain in DOMAIN_WEIGHTS:
            keys = [
                key
                for key in source.keys() & target.keys()
                if key.startswith(f"{domain}:")
            ]
            if not keys:
                continue
            mean_squared = sum(
                (self._normalized(source, key) - self._normalized(target, key)) ** 2
                for key in keys
            ) / len(keys)
            distances[domain] = math.sqrt(mean_squared)
        weight_total = sum(DOMAIN_WEIGHTS[domain] for domain in distances)
        distance = (
            sum(DOMAIN_WEIGHTS[domain] * value for domain, value in distances.items())
            / weight_total
            if weight_total
            else 1.0
        )
        shared = len(source.keys() & target.keys())
        return distance, distances, shared

    def _shared_tasks(self, source_code: str, target_code: str) -> list[str]:
        source_rows = self.task_token_rows.get(source_code, [])
        target_rows = self.task_token_rows.get(target_code, [])
        scored: list[tuple[float, int, str]] = []
        for statement, target_tokens in target_rows:
            best_overlap = 0
            best_union = 0
            for _, source_tokens in source_rows:
                overlap = len(target_tokens & source_tokens)
                union = len(target_tokens | source_tokens)
                if (overlap, -union) > (best_overlap, -best_union):
                    best_overlap, best_union = overlap, union
            if best_overlap >= 2 and best_union:
                scored.append((best_overlap / best_union, best_overlap, statement))
        scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
        output: list[str] = []
        for _, _, statement in scored:
            if statement not in output:
                output.append(statement)
            if len(output) == 3:
                break
        return output

    def _confidence(
        self, source_code: str, target_code: str, shared_elements: int
    ) -> str:
        source = self.profile_source.get(source_code)
        target = self.profile_source.get(target_code)
        if source == "exact" and target == "exact" and shared_elements >= 100:
            return "High"
        if shared_elements >= 80:
            return "Moderate"
        return "Limited"

    def _training_hint(
        self, distances: dict[str, float], software_overlap: float
    ) -> str:
        general = (
            sum(
                distances.get(domain, 0.0)
                for domain in ("essential", "transferable", "abilities")
            )
            / 3
        )
        specific = (
            sum(distances.get(domain, 0.0) for domain in ("knowledge", "activities"))
            / 2
        )
        if specific > general + 0.05 or software_overlap < 0.12:
            return "The larger gap is task-specific. Compare the shared tasks and prioritize hands-on practice or an integrated work sample."
        if general > specific + 0.05:
            return "The broader skills profile differs more. Strengthen the transferable reasoning, communication, or problem-solving evidence before specializing."
        return "The profiles are broadly close. Use the shared tasks to choose a focused work sample and verify any tool-specific requirements."

    def _candidate(self, source_code: str, target_code: str) -> dict[str, object]:
        distance, domain_distances, shared_elements = self._structural_distance(
            source_code, target_code
        )
        software_union = self.software.get(source_code, set()) | self.software.get(
            target_code, set()
        )
        software_overlap = (
            len(
                self.software.get(source_code, set())
                & self.software.get(target_code, set())
            )
            / len(software_union)
            if software_union
            else 0.0
        )
        task_similarity = _jaccard(
            self.task_tokens.get(source_code, set()),
            self.task_tokens.get(target_code, set()),
        )
        composite_distance = 0.85 * distance + 0.15 * (1.0 - software_overlap)
        source_tasks = len(self.task_token_rows.get(source_code, []))
        target_tasks = len(self.task_token_rows.get(target_code, []))
        row = self.rows_by_code[target_code]
        return {
            "occupation": _snapshot(row, self.profile_source.get(target_code, "")),
            "structured_distance": round(distance, 3),
            "structured_similarity": round(max(0.0, 1.0 - distance), 3),
            "software_overlap": round(software_overlap, 3),
            "task_similarity": round(task_similarity, 3),
            "composite_distance": round(composite_distance, 3),
            "shared_profile_elements": shared_elements,
            "source_task_count": source_tasks,
            "target_task_count": target_tasks,
            "shared_task_evidence": self._shared_tasks(source_code, target_code),
            "training_hint": self._training_hint(domain_distances, software_overlap),
            "confidence": self._confidence(source_code, target_code, shared_elements),
        }

    def bridge(self, source_code: str, limit: int = 6) -> dict[str, object]:
        cache_key = (source_code, limit)
        if cache_key in self._cache:
            return self._cache[cache_key]
        source_row = self.rows_by_code.get(source_code)
        if not source_row:
            return {"available": False, "error": "occupation_not_found"}
        if not self.available or source_code not in self.profiles:
            return {
                "available": False,
                "source": _snapshot(source_row),
                "error": "structured_onet_profiles_unavailable",
                "message": "The structured O*NET profile files are not available in this build.",
            }
        candidates = [
            target_code
            for target_code in self.rows_by_code
            if target_code != source_code and target_code in self.profiles
        ]
        scored = [
            self._candidate(source_code, target_code) for target_code in candidates
        ]
        scored.sort(
            key=lambda item: (
                item["composite_distance"],
                -item["software_overlap"],
                -item["task_similarity"],
                str(item["occupation"]["title"]).casefold(),
            )
        )
        safe_limit = max(0, min(int(limit), 12))
        result = {
            "available": True,
            "source": _snapshot(source_row, self.profile_source.get(source_code, "")),
            "candidates": scored[:safe_limit],
            "candidate_count": len(scored),
            "method": {
                "primary": "Weighted normalized distance across O*NET Essential Skills, Transferable Skills, Knowledge, Abilities, and Work Activities importance ratings.",
                "secondary": "Software overlap is a separate Jaccard-style evidence signal and lightly regularizes the ranking.",
                "task_evidence": "Shared task statements are supplemental evidence, not the primary distance measure.",
                "interpretation": "This is a descriptive occupation bridge for pathway discovery. It is not a worker ability estimate, hiring probability, or employment forecast.",
                "source": "O*NET 30.3 structured ratings and task statements.",
            },
        }
        self._cache[cache_key] = result
        return result
