from __future__ import annotations

import csv
import io
import json
import math
import re
import zipfile
from pathlib import Path
from typing import Iterable

from .demo import FIELDS, TASK_FIELDS, demo_rows, demo_tasks
from .io import read_csv, sha256, write_csv, write_json
from .occupation_context import load_alias_registry, validate_alias_registry
from .resources import resource_path


def _value(row: dict[str, object], *names: str) -> str:
    def clean(value: object) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value).strip().lower()).strip()

    lowered = {clean(key): value for key, value in row.items()}
    for name in names:
        key = clean(name)
        if key in lowered and lowered[key] not in (None, ""):
            return str(lowered[key]).strip()
    return ""


def _number(value: object, *, non_negative: bool = False) -> float | None:
    if value in (None, "", "*", "**", "#", "–", "—"):
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    try:
        parsed = float(cleaned) if cleaned else None
        if parsed is None or not math.isfinite(parsed):
            return None
        return None if non_negative and parsed < 0 else parsed
    except ValueError:
        return None


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _find_file(root: Path, names: Iterable[str]) -> Path | None:
    wanted = {name.lower() for name in names}
    for path in root.rglob("*"):
        if path.is_file() and path.name.lower() in wanted:
            return path
    return None


def _extract_onet_zip(zip_path: Path, temp_dir: Path) -> Path:
    temp_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(temp_dir)
    return temp_dir


def _load_onet(raw_dir: Path) -> list[dict[str, object]]:
    occupation_file = _find_file(
        raw_dir, ["Occupation Data.txt", "occupation data.txt"]
    )
    if not occupation_file:
        zip_path = raw_dir / "onet_30_3_text.zip"
        if zip_path.exists():
            _extract_onet_zip(zip_path, raw_dir / "onet_30_3_text")
            occupation_file = _find_file(
                raw_dir / "onet_30_3_text",
                ["Occupation Data.txt", "occupation data.txt"],
            )
    if not occupation_file:
        raise FileNotFoundError(
            "O*NET occupation data not found. Put Occupation Data.txt or onet_30_3_text.zip in data/raw."
        )
    rows = []
    for row in _read_tsv(occupation_file):
        code = _value(row, "O*NET-SOC Code", "O*NET SOC Code")
        if not code or code.lower().startswith("code"):
            continue
        rows.append(
            {
                "onet_soc_code": code,
                "title": _value(row, "Title"),
                "description": _value(row, "Description"),
            }
        )
    return rows


def _load_tasks(raw_dir: Path) -> list[dict[str, str]]:
    task_file = _find_file(raw_dir, ["Task Statements.txt", "task statements.txt"])
    if not task_file:
        zip_path = raw_dir / "onet_30_3_text.zip"
        if zip_path.exists():
            _extract_onet_zip(zip_path, raw_dir / "onet_30_3_text")
            task_file = _find_file(
                raw_dir / "onet_30_3_text",
                ["Task Statements.txt", "task statements.txt"],
            )
    if not task_file:
        raise FileNotFoundError(
            "O*NET task data not found. Put Task Statements.txt or onet_30_3_text.zip in data/raw."
        )
    rows = []
    for row in _read_tsv(task_file):
        code = _value(row, "O*NET-SOC Code", "O*NET SOC Code")
        task_id = _value(row, "Task ID", "task id")
        statement = _value(row, "Task", "Task Statement", "task statement")
        if not code or not task_id or not statement:
            continue
        rows.append(
            {
                "onet_soc_code": code,
                "task_id": task_id,
                "task_statement": statement,
                "task_type": _value(row, "Task Type", "task type"),
                "incumbents_responding": _value(
                    row, "Incumbents Responding", "incumbents responding"
                ),
                "task_date": _value(row, "Date", "task date"),
                "domain_source": _value(row, "Domain Source", "domain source"),
                "onet_version": "30.3",
                "source_file": task_file.name,
                "task_quality_flags": "",
            }
        )
    return rows


def _load_crosswalk(raw_dir: Path) -> dict[str, list[str]]:
    workbook = raw_dir / "onet_soc_2019_to_2018.xlsx"
    if not workbook.exists():
        candidates = list(raw_dir.glob("*.xlsx"))
        workbook = next(
            (
                path
                for path in candidates
                if "cross" in path.name.lower() or "soc" in path.name.lower()
            ),
            workbook,
        )
    if not workbook.exists():
        return {}
    try:
        from openpyxl import load_workbook
    except ImportError as error:
        raise RuntimeError(
            "Crosswalk parsing requires optional dependency: pip install -e .[excel]"
        ) from error
    workbook_handle = load_workbook(workbook, read_only=True, data_only=True)
    sheet = workbook_handle.active
    rows = list(sheet.iter_rows(values_only=True))
    workbook_handle.close()
    header_index = next(
        (
            index
            for index, row in enumerate(rows)
            if any("2019" in str(cell) and "Code" in str(cell) for cell in row)
        ),
        0,
    )
    header = [str(cell or "").strip() for cell in rows[header_index]]
    source_index = next(
        (
            index
            for index, item in enumerate(header)
            if "2019" in item and "code" in item.lower()
        ),
        0,
    )
    target_index = next(
        (
            index
            for index, item in enumerate(header)
            if "2018" in item and "code" in item.lower()
        ),
        1,
    )
    mapping: dict[str, list[str]] = {}
    for row in rows[header_index + 1 :]:
        if len(row) <= max(source_index, target_index):
            continue
        source = str(row[source_index] or "").strip()
        target = str(row[target_index] or "").strip()
        if source and target:
            mapping.setdefault(source, []).append(target)
    return mapping


def _load_aioe(raw_dir: Path) -> dict[str, float]:
    candidates = [raw_dir / "aioe.csv", raw_dir / "AIOE.csv"]
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if path:
        rows = read_csv(path)
    else:
        workbook = raw_dir / "aioe_data_appendix.xlsx"
        if not workbook.exists():
            return {}
        try:
            from openpyxl import load_workbook
        except ImportError as error:
            raise RuntimeError(
                "AIOE workbook parsing requires optional dependency: pip install -e .[excel]"
            ) from error
        workbook_handle = load_workbook(workbook, read_only=True, data_only=True)
        sheet = workbook_handle["Appendix A"]
        values = list(sheet.iter_rows(values_only=True))
        workbook_handle.close()
        rows = [dict(zip(values[0], row)) for row in values[1:]]
    result = {}
    for row in rows:
        code = _value(row, "soc", "soc_code", "soc 2018 code", "occupation code")
        # AIOE is standardized across occupations.  Negative values are valid
        # and mean below-average exposure; they are not missing observations.
        score = _number(_value(row, "aioe", "ai exposure", "exposure"))
        if code and score is not None:
            result[code] = score
    return result


def _load_aioe_soc_bridge() -> dict[str, object]:
    """Load the conservative BLS 2010-to-2018 bridge packaged with Atlas."""

    with resource_path("aioe_soc_2010_to_2018.json").open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("AIOE SOC bridge must be a JSON object")
    return value


def _bridge_aioe_to_soc_2018(
    source_scores: dict[str, float], target_soc_codes: set[str]
) -> tuple[dict[str, float], dict[str, set[str]], dict[str, object]]:
    """Bridge AIOE's SOC 2010 codes without inventing split/merge allocations."""

    bridge = _load_aioe_soc_bridge()
    one_to_one = {
        str(source): str(target)
        for source, target in dict(bridge.get("one_to_one", {})).items()
    }
    ambiguous = {
        str(source): {str(target) for target in targets}
        for source, targets in dict(bridge.get("ambiguous", {})).items()
        if isinstance(targets, list)
    }
    scores: dict[str, float] = {}
    flags: dict[str, set[str]] = {}
    for source_code, score in source_scores.items():
        if source_code in ambiguous:
            for target_code in ambiguous[source_code] & target_soc_codes:
                flags.setdefault(target_code, set()).add("aioe_crosswalk_ambiguous")
            continue
        target_code = one_to_one.get(source_code)
        if target_code is None:
            # The packaged bridge is generated from the entire official BLS
            # crosswalk. A code absent from both classifications is not safe
            # to treat as continuous; fail closed instead of inventing a map.
            continue
        if target_code not in target_soc_codes:
            continue
        if target_code in scores:
            scores.pop(target_code, None)
            flags.setdefault(target_code, set()).add("aioe_crosswalk_ambiguous")
            continue
        scores[target_code] = score
    metadata = {
        "source_soc_vintage": bridge.get("source_soc_vintage", "2010"),
        "target_soc_vintage": bridge.get("target_soc_vintage", "2018"),
        "official_crosswalk_url": bridge.get("official_crosswalk_url", ""),
        "method": bridge.get("method", ""),
        "official_crosswalk_classification": bridge.get("classification", {}),
        "one_to_one_mapped_scores": sum(
            code in one_to_one and target in scores
            for code, target in one_to_one.items()
        ),
        "ambiguous_target_count": len(flags),
    }
    return scores, flags, metadata


def _apply_relative_aioe_scale(
    rows: list[dict[str, object]], *, source_values: Iterable[float] | None = None
) -> dict[str, object]:
    """Replace signed source AIOE with a user-facing, order-preserving scale.

    Source AIOE is standardized around zero, which is statistically useful but
    easy to mistake for a negative likelihood or a prediction of job loss.
    The published occupation field therefore uses a release-specific 0--100
    min--max display scale. The transformation is recorded in the manifest.
    """

    values = list(source_values or ())
    if not values:
        values = [
            float(row["ai_exposure"])
            for row in rows
            if row.get("ai_exposure") not in (None, "")
        ]
    if not values:
        for row in rows:
            row["ai_exposure_display_scale"] = ""
        return {
            "method": "relative_0_100_min_max",
            "source_min": None,
            "source_max": None,
            "interpretation": "No source AIOE values were available.",
        }
    source_min = min(values)
    source_max = max(values)
    spread = source_max - source_min
    for row in rows:
        raw = row.get("ai_exposure")
        if raw in (None, ""):
            row["ai_exposure_display_scale"] = ""
            continue
        value = float(raw)
        row["ai_exposure"] = round(
            50.0 if spread == 0 else 100 * (value - source_min) / spread,
            6,
        )
        row["ai_exposure_display_scale"] = "relative_0_100_min_max"
        if row.get("ai_exposure_source"):
            source = str(row["ai_exposure_source"])
            row["ai_exposure_source"] = (
                source if source.endswith("_relative_display") else f"{source}_relative_display"
            )
    return {
        "method": "relative_0_100_min_max",
        "source_min": source_min,
        "source_max": source_max,
        "interpretation": (
            "A 0--100 relative display scale derived from the signed, "
            "standardized AIOE values in this release. It preserves ordering; "
            "it is not a probability, replacement risk, or forecast of job loss."
        ),
    }


def _read_csv_or_zip(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() != ".zip":
        return read_csv(path)
    with zipfile.ZipFile(path) as archive:
        spreadsheet_names = [
            name for name in archive.namelist() if name.lower().endswith(".xlsx")
        ]
        if spreadsheet_names:
            try:
                from openpyxl import load_workbook
            except ImportError as error:
                raise RuntimeError(
                    "XLSX parsing requires optional dependency: pip install -e .[excel]"
                ) from error
            workbook_handle = load_workbook(
                io.BytesIO(archive.read(spreadsheet_names[0])),
                read_only=True,
                data_only=True,
            )
            sheet = workbook_handle.active
            values = list(sheet.iter_rows(values_only=True))
            workbook_handle.close()
            if not values:
                return []
            header = [str(cell or "").strip() for cell in values[0]]
            return [
                dict(zip(header, row))
                for row in values[1:]
                if any(cell not in (None, "") for cell in row)
            ]
        names = [
            name
            for name in archive.namelist()
            if name.lower().endswith((".csv", ".txt"))
        ]
        if not names:
            return []
        with archive.open(names[0]) as raw:
            content = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
            sample = content.read(2048)
            content.seek(0)
            delimiter = "\t" if "\t" in sample else ","
            return list(csv.DictReader(content, delimiter=delimiter))


def _load_oews(raw_dir: Path) -> dict[str, dict[str, float | None]]:
    candidates = [raw_dir / "bls_oews_may_2025.zip", raw_dir / "bls_oews.csv"]
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if not path:
        return {}
    result = {}
    for row in _read_csv_or_zip(path):
        code = _value(row, "occ code", "occ_code", "soc code", "occupation code")
        if not code or code.lower() in {"code", "occ_code"}:
            continue
        result[code] = {
            "employment_2024": _number(
                _value(row, "tot emp", "total employment", "employment"),
                non_negative=True,
            ),
            "median_annual_wage": _number(
                _value(row, "a median", "median annual wage", "annual median wage"),
                non_negative=True,
            ),
        }
    return result


def _load_projections(raw_dir: Path) -> dict[str, dict[str, float | None]]:
    candidates = [
        raw_dir / "bls_projections_2024_2034.xlsx",
        raw_dir / "bls_projections_2024_2034.csv",
    ]
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if not path:
        return {}
    if path.suffix.lower() == ".csv":
        rows = read_csv(path)
    else:
        try:
            from openpyxl import load_workbook
        except ImportError as error:
            raise RuntimeError(
                "Projection parsing requires optional dependency: pip install -e .[excel]"
            ) from error
        workbook_handle = load_workbook(path, read_only=True, data_only=True)
        sheet = (
            workbook_handle["Table 1.2"]
            if "Table 1.2" in workbook_handle.sheetnames
            else workbook_handle.active
        )
        values = list(sheet.iter_rows(values_only=True))
        workbook_handle.close()
        header_index = next(
            (
                index
                for index, row in enumerate(values)
                if any(
                    "2024 national employment matrix code" in str(cell).lower()
                    for cell in row
                )
                and any(str(cell).strip().lower() == "employment, 2024" for cell in row)
            ),
            0,
        )
        header = [str(cell or "").strip() for cell in values[header_index]]
        rows = [dict(zip(header, row)) for row in values[header_index + 1 :]]
    result = {}
    for row in rows:
        annual_openings_thousands = _number(
            _value(
                row,
                "Occupational openings, 2024-34 annual average",
                "occupational openings annual average",
            ),
            non_negative=True,
        )
        code = _value(
            row,
            "2024 National Employment Matrix code",
            "national employment matrix code",
            "occupation code",
            "soc code",
        )
        if not code or code.lower() in {"code", "occupation code"}:
            continue
        result[code] = {
            "projected_employment_2024_thousands": _number(
                _value(row, "Employment, 2024", "employment 2024"),
                non_negative=True,
            ),
            "projected_employment_2034_thousands": _number(
                _value(row, "Employment, 2034", "employment 2034"),
                non_negative=True,
            ),
            "employment_change_2024_2034_pct": _number(
                _value(
                    row,
                    "Employment change, percent, 2024-34",
                    "employment change percent 2024 34",
                )
            ),
            "annual_openings_2024_2034": (
                annual_openings_thousands * 1000
                if annual_openings_thousands is not None
                else None
            ),
            "projection_median_annual_wage": _number(
                _value(
                    row,
                    "Median annual wage, dollars, 2024",
                    "median annual wage dollars 2024",
                ),
                non_negative=True,
            ),
        }
    return result


def build_dataset(
    raw_dir: Path, processed_dir: Path, demo: bool = False
) -> dict[str, object]:
    processed_dir.mkdir(parents=True, exist_ok=True)
    if demo:
        rows = demo_rows()
        tasks = demo_tasks()
        source_flags = {"mode": "demo", "rows": len(rows)}
    else:
        onet = _load_onet(raw_dir)
        tasks = _load_tasks(raw_dir)
        occupation_codes = {str(item["onet_soc_code"]) for item in onet}
        for task in tasks:
            if task["onet_soc_code"] not in occupation_codes:
                task["task_quality_flags"] = "task_without_occupation_record"
        crosswalk = _load_crosswalk(raw_dir)
        soc_to_onet: dict[str, set[str]] = {}
        for source_code, targets in crosswalk.items():
            for target_code in set(targets):
                soc_to_onet.setdefault(target_code, set()).add(source_code)
        aioe_source = _load_aioe(raw_dir)
        oews = _load_oews(raw_dir)
        projections = _load_projections(raw_dir)
        # AIOE is an independent source layer. Its availability follows the
        # O*NET-to-2018-SOC crosswalk, not whether wage or projection records
        # happen to be published for the same SOC code.
        target_soc_codes = {
            str(target).strip()
            for targets in crosswalk.values()
            for target in targets
            if str(target).strip()
        }
        aioe, aioe_flags, aioe_bridge = _bridge_aioe_to_soc_2018(
            aioe_source, target_soc_codes
        )
        rows = []
        for item in onet:
            codes = [
                code
                for code in list(
                    dict.fromkeys(crosswalk.get(str(item["onet_soc_code"]), [""]))
                )
                if str(code).strip()
            ]
            codes = codes or [""]
            crosswalk_weight = 1.0 / len([code for code in codes if code]) if any(codes) else 1.0
            for soc_code in codes or [""]:
                wage = oews.get(soc_code, {})
                projection = projections.get(soc_code, {})
                exposure = aioe.get(soc_code)
                flags = []
                flags.extend(sorted(aioe_flags.get(soc_code, set())))
                if len([code for code in codes if code]) > 1:
                    flags.append("multiple_soc_crosswalk")
                    flags.append("uniform_crosswalk_fallback")
                if not soc_code:
                    flags.append("missing_crosswalk")
                if soc_code and len(soc_to_onet.get(soc_code, set())) > 1:
                    flags.append("shared_soc_crosswalk")
                if exposure is None:
                    flags.append("missing_aioe")
                if not wage:
                    flags.append("missing_oews")
                if not projection:
                    flags.append("missing_projections")
                rows.append(
                    {
                        "onet_soc_code": item["onet_soc_code"],
                        "soc_2018_code": soc_code,
                        "crosswalk_weight": crosswalk_weight,
                        "title": item["title"],
                        "description": item["description"],
                        "ai_exposure": exposure,
                        "ai_exposure_source": (
                            "AIOE_SOC2010_to_SOC2018_relative_display"
                            if exposure is not None
                            else ""
                        ),
                        "ai_exposure_soc_vintage": "2010_to_2018_official_bridge",
                        "employment_2024": wage.get("employment_2024"),
                        "projected_employment_2024_thousands": projection.get(
                            "projected_employment_2024_thousands"
                        ),
                        "projected_employment_2034_thousands": projection.get(
                            "projected_employment_2034_thousands"
                        ),
                        "employment_change_2024_2034_pct": projection.get(
                            "employment_change_2024_2034_pct"
                        ),
                        "annual_openings_2024_2034": projection.get(
                            "annual_openings_2024_2034"
                        ),
                        "median_annual_wage": wage.get("median_annual_wage")
                        or projection.get("projection_median_annual_wage"),
                        "onet_version": "30.3",
                        "wage_vintage": "May 2025",
                        "projection_vintage": "2024-2034",
                        "crosswalk_method": "official_onet_crosswalk",
                        "data_quality_flags": ";".join(flags),
                    }
                )
        source_flags = {
            "mode": "public_raw",
            "rows": len(rows),
            "onet_rows": len(onet),
            "task_rows": len(tasks),
            "task_occupations": len({task["onet_soc_code"] for task in tasks}),
            "task_unknown_occupation_rows": sum(
                task["task_quality_flags"] == "task_without_occupation_record"
                for task in tasks
            ),
            "crosswalk_sources": len(crosswalk),
            "aioe_source_rows": len(aioe_source),
            "aioe_rows_after_soc_bridge": len(aioe),
            "aioe_soc_bridge": aioe_bridge,
            "oews_rows": len(oews),
            "projection_rows": len(projections),
        }
        source_flags["aioe_display"] = _apply_relative_aioe_scale(
            rows, source_values=aioe_source.values()
        )
    if demo:
        source_flags["aioe_display"] = {
            "method": "relative_0_100_min_max",
            "interpretation": (
                "Demo values use the same 0--100 relative display convention; "
                "they are not probabilities or job-loss forecasts."
            ),
        }
    if not demo:
        validate_alias_registry(load_alias_registry(), rows)
        missing_layers = [
            label
            for label, values in (
                ("O*NET occupations", onet),
                ("O*NET tasks", tasks),
                ("O*NET-to-SOC crosswalk", crosswalk),
                ("AIOE exposure", aioe),
                ("BLS OEWS", oews),
                ("BLS Employment Projections", projections),
            )
            if not values
        ]
        if missing_layers:
            raise ValueError(
                "full build requires every registered data layer; missing or "
                "unreadable: "
                + ", ".join(missing_layers)
                + ". Run 'atlas download' and resolve every failed source first."
            )
    count = write_csv(processed_dir / "occupations.csv", rows, FIELDS)
    task_count = write_csv(processed_dir / "tasks.csv", tasks, TASK_FIELDS)
    manifest = {
        "schema": FIELDS,
        "row_count": count,
        "task_schema": TASK_FIELDS,
        "task_row_count": task_count,
        "build": source_flags,
        "sha256": sha256(processed_dir / "occupations.csv"),
        "tasks_sha256": sha256(processed_dir / "tasks.csv"),
    }
    write_json(processed_dir / "data_manifest.json", manifest)
    return manifest
