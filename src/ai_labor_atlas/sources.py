from __future__ import annotations

import time
import urllib.error
import urllib.request
import io
import zipfile
from typing import Callable
from datetime import datetime, timezone
from pathlib import Path

from .io import read_json, write_json


USER_AGENT = "ai-labor-atlas/0.5.0 (reproducible research; contact via GitHub issues)"
SOURCE_INTEGRITY_FAILURE = "new_upstream_version_requires_review"


def download_file(
    url: str,
    destination: Path,
    retries: int = 3,
    validate_payload: Callable[[bytes], None] | None = None,
) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
            if not payload or (
                destination.suffix == ".zip" and not payload.startswith(b"PK")
            ):
                raise ValueError("empty or invalid source payload")
            if validate_payload:
                validate_payload(payload)
            if destination.exists():
                previous = destination.with_suffix(destination.suffix + ".previous")
                if not previous.exists():
                    previous.write_bytes(destination.read_bytes())
            destination.write_bytes(payload)
            return {
                "status": "downloaded",
                "url": url,
                "path": str(destination),
                "file_bytes": len(payload),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            ValueError,
            zipfile.BadZipFile,
            KeyError,
            ImportError,
        ) as error:
            last_error = str(error)
            if attempt < retries:
                time.sleep(attempt)
    return {
        "status": "failed",
        "url": url,
        "path": str(destination),
        "error": last_error,
    }


def validate_projection_archive(payload: bytes) -> None:
    """Reject the wrong projection vintage before replacing a retained archive."""
    from openpyxl import load_workbook

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [
            name
            for name in archive.namelist()
            if Path(name).name.lower() == "occupation.xlsx"
        ]
        if len(members) != 1:
            raise ValueError(
                "Expected one occupation.xlsx in the official historical archive"
            )
        workbook = load_workbook(
            io.BytesIO(archive.read(members[0])), read_only=True, data_only=True
        )
        try:
            sheet = workbook["Table 1.2"]
            valid = any(
                {
                    "2024 National Employment Matrix code",
                    "Employment, 2024",
                    "Employment, 2034",
                }.issubset({str(v).strip() for v in row})
                for row in sheet.iter_rows(max_row=10, values_only=True)
            )
        finally:
            workbook.close()
        if not valid:
            raise ValueError(
                "Expected 2024–2034 projection vintage; previous source preserved"
            )


def download_registered_sources(config_path: Path, raw_dir: Path) -> dict[str, object]:
    config = read_json(config_path)
    results = []
    for source in config["sources"]:
        url = source.get("download_url")
        filename = source.get("raw_filename")
        if not url or not filename:
            results.append(
                {
                    "id": source["id"],
                    "status": "manual_or_unverified",
                    "landing_url": source.get("landing_url"),
                }
            )
            continue
        result = download_file(
            url,
            raw_dir / filename,
            validate_payload=validate_projection_archive
            if source["id"] == "bls_projections"
            else None,
        )
        result["id"] = source["id"]
        result["version"] = source.get("version")
        result["landing_url"] = source.get("landing_url")
        if result.get("status") == "failed":
            result["next_step"] = (
                "Download the registered file from landing_url, inspect its version "
                f"and schema, then place it at {raw_dir / filename}."
            )
        results.append(result)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": str(config_path),
        "results": results,
    }
    write_json(raw_dir.parent / "download_manifest.json", manifest)
    return manifest
