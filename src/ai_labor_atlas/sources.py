from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .io import read_json, write_json


USER_AGENT = "ai-labor-atlas/0.3.0 (reproducible research; contact via GitHub issues)"
SOURCE_INTEGRITY_FAILURE = "new_upstream_version_requires_review"


def download_file(
    url: str,
    destination: Path,
    retries: int = 3,
    expected_sha256: str | None = None,
) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
            actual_sha256 = sha256_bytes(payload)
            if expected_sha256 and actual_sha256 != expected_sha256:
                return {
                    "status": SOURCE_INTEGRITY_FAILURE,
                    "url": url,
                    "path": str(destination),
                    "expected_sha256": expected_sha256,
                    "actual_sha256": actual_sha256,
                }
            destination.write_bytes(payload)
            return {
                "status": "downloaded_verified" if expected_sha256 else "downloaded_unverified",
                "url": url,
                "path": str(destination),
                "sha256": actual_sha256,
                "expected_sha256": expected_sha256,
            }
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = str(error)
            if attempt < retries:
                time.sleep(attempt)
    return {
        "status": "failed",
        "url": url,
        "path": str(destination),
        "error": last_error,
    }


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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
            expected_sha256=(str(source["sha256"]) if source.get("sha256") else None),
        )
        result["id"] = source["id"]
        result["version"] = source.get("version")
        results.append(result)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": str(config_path),
        "results": results,
    }
    write_json(raw_dir.parent / "download_manifest.json", manifest)
    return manifest
