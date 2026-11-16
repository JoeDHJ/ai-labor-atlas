"""BLS national industry-occupation matrix: source baseline only, never projections."""

from __future__ import annotations

import re
import math
from collections import defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from .io import read_csv, write_csv, write_json
from .resources import resource_path
from .sources import download_file

MATRICES = (
    ("31-330", "Manufacturing", "manufacturing_matrix.html"),
    ("540000", "Professional and business services", "professional_matrix.html"),
    ("550000", "Professional and business services", "industry_550000.html"),
    ("560000", "Professional and business services", "industry_560000.html"),
)


class MatrixParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.cell: list[str] | None = None
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "table" and dict(attrs).get("id") == "mytable":
            self.active = True
        if self.active and tag == "tr":
            self.row = []
        if self.active and tag in ("td", "th"):
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        if self.active and tag == "tr" and self.row:
            self.rows.append(self.row)
        if tag == "table":
            self.active = False


def parse_matrix(
    text: str, source_id: str, industry: str, retrieved_at: str
) -> list[dict]:
    parser = MatrixParser()
    parser.feed(text)
    if not parser.rows or "2025 Employment" not in parser.rows[0]:
        raise ValueError(
            f"{source_id}: expected 2025 baseline header; review source vintage"
        )
    records, seen = [], set()
    for row in parser.rows[1:]:
        if len(row) < 7 or not re.fullmatch(r"\d\d-\d{4}", row[1]):
            continue
        if row[2] != "Line Item" and row[1] != "00-0000":
            continue  # Summary hierarchy must never be added to leaf occupations.
        if row[1] in seen:
            raise ValueError(f"{source_id}: duplicate occupation")
        seen.add(row[1])
        try:
            value = float(row[3].replace(",", ""))
        except ValueError as exc:
            raise ValueError(
                f"{source_id}: missing/nonnumeric baseline employment"
            ) from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{source_id}: nonfinite or negative employment")
        records.append(
            {
                "schema_version": "portfolio.v1",
                "source_id": f"bls_matrix_{source_id}",
                "source_url": f"https://data.bls.gov/projections/nationalMatrix?queryParams={source_id}&ioType=i",
                "retrieved_at": retrieved_at,
                "source_vintage": "2025-2035 matrix, 2025 baseline",
                "period": "2025",
                "geography": "US",
                "industry": industry,
                "industry_source_id": source_id,
                "occupation_code": row[1],
                "title": row[0],
                "occupation_type": row[2],
                "employment_thousands": value,
                "unit_of_observation": "industry_occupation_year",
                "unit": "thousand_jobs",
                "taxonomy": "BLS National Employment Matrix 2025 (SOC2018 aligned)",
                "status": "observed",
            }
        )
    if "00-0000" not in seen or len(records) < 2:
        raise ValueError(f"{source_id}: no complete baseline matrix")
    return records


def refresh_staffing(raw_dir: Path, destination: Path, *, fetch: bool = True) -> dict:
    records, sources = [], []
    for code, industry, filename in MATRICES:
        path = raw_dir / filename
        if fetch:
            candidate = path.with_suffix(".candidate.html")
            url = f"https://data.bls.gov/projections/nationalMatrix?queryParams={code}&ioType=i"
            result = download_file(url, candidate, retries=2)
            if result["status"] != "downloaded":
                raise ValueError(f"{code}: {result.get('error')}")
            retrieved = str(result["retrieved_at"])
            parsed = parse_matrix(
                candidate.read_text(encoding="utf-8"), code, industry, retrieved
            )
            if path.exists() and not path.with_suffix(".previous.html").exists():
                path.with_suffix(".previous.html").write_bytes(path.read_bytes())
            candidate.replace(path)
        else:
            retrieved = datetime.fromtimestamp(
                path.stat().st_mtime, timezone.utc
            ).isoformat()
            parsed = parse_matrix(
                path.read_text(encoding="utf-8"), code, industry, retrieved
            )
        records.extend(parsed)
        sources.append(
            {
                "source_id": code,
                "path": str(path),
                "retrieved_at": retrieved,
                "source_url": f"https://data.bls.gov/projections/nationalMatrix?queryParams={code}&ioType=i",
                "source_vintage": "2025-2035 matrix, 2025 baseline",
                "file_bytes": path.stat().st_size,
                "rows": len(parsed),
            }
        )
    write_csv(destination / "industry_staffing.csv", records, list(records[0]))
    manifest = {
        "schema_version": "portfolio.v1",
        "sources": sources,
        "rows": len(records),
        "note": "2025 employment baseline only. Projected 2035 cells are not imported. Suppressed small/confidential/poor-quality cells are not reconstructed.",
    }
    write_json(destination / "staffing_manifest.json", manifest)
    return manifest


def load_staffing(research_dir: Path) -> list[dict]:
    path = research_dir / "industry_staffing.csv"
    if not path.exists():
        path = resource_path("industry_staffing.csv")
    return read_csv(path)


def aggregate_staffing(records: list[dict]) -> dict[str, tuple[list[dict], float]]:
    """Sum disjoint NAICS 54,55,56, retaining published total as coverage denominator."""
    groups = defaultdict(lambda: defaultdict(float))
    totals = defaultdict(float)
    seen = set()
    for row in records:
        key = row["industry_source_id"], row["occupation_code"]
        if key in seen:
            raise ValueError("duplicate industry-occupation baseline cell")
        seen.add(key)
        jobs = float(row["employment_thousands"]) * 1000
        if row["occupation_code"] == "00-0000":
            totals[row["industry"]] += jobs
        elif row["occupation_type"] == "Line Item":
            groups[row["industry"]][row["occupation_code"]] += jobs
    return {
        industry: (
            [
                {"soc_2018_code": code, "employment_2024": jobs}
                for code, jobs in values.items()
            ],
            totals[industry],
        )
        for industry, values in groups.items()
    }
