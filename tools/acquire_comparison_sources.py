"""Explicit acquisition of pinned public aggregate research files; no conversations."""

from __future__ import annotations

import json
import io
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MS_REVISION = "550c00c9d1b054ac78b87da3a26165bace334779"


def acquire(hf_revision: str) -> None:
    target = ROOT / "data/raw/comparison"
    target.mkdir(parents=True, exist_ok=True)
    ms = f"https://raw.githubusercontent.com/microsoft/working-with-ai/{MS_REVISION}/"
    hf = f"https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/{hf_revision}/"
    sources = [
        ("microsoft_scores.csv", ms + "ai_applicability_scores.csv"),
        ("microsoft_iwa.csv", ms + "iwa_metrics.csv"),
        ("microsoft_weights.csv", ms + "soc_iwa_weights.csv"),
        ("microsoft_nonphysical_weights.csv", ms + "soc_iwa_nonphysical_weights.csv"),
        ("microsoft_soc_iwas.csv", ms + "soc_to_iwas.csv"),
        ("microsoft_physical.csv", ms + "physical_tasks.csv"),
        ("microsoft_notice.md", ms + "NOTICE.md"),
        ("microsoft_license.txt", ms + "LICENSE.txt"),
        ("microsoft_readme.md", ms + "README.md"),
        (
            "anthropic_task_mappings.csv",
            hf + "release_2025_02_10/onet_task_mappings.csv",
        ),
        (
            "anthropic_task_statements.csv",
            hf + "release_2025_02_10/onet_task_statements.csv",
        ),
        ("anthropic_readme.md", hf + "release_2025_02_10/README.md"),
        (
            "onet_2010_to_2019.csv",
            "https://www.onetcenter.org/taxonomy/2019/walk/2010_to_2019_Crosswalk.csv?fmt=csv",
        ),
        (
            "onet_29_0.zip",
            "https://www.onetcenter.org/dl_files/database/db_29_0_text.zip",
        ),
    ]

    def fetch(item):
        name, url = item
        for attempt in range(3):
            try:
                payload = urllib.request.urlopen(url, timeout=60).read()
                if len(payload) < 100:
                    raise ValueError(f"Empty source: {name}")
                (target / name).write_bytes(payload)
                if name == "onet_29_0.zip":
                    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                        member = next(
                            n
                            for n in archive.namelist()
                            if n.endswith("/Task Statements.txt")
                        )
                        (target / "benchmark_tasks_29_0.txt").write_bytes(
                            archive.read(member)
                        )
                print(f"Acquired {name}: {len(payload):,} bytes", flush=True)
                return {
                    "file": name,
                    "url": url,
                    "bytes": len(payload),
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                }
            except (OSError, ValueError):
                if attempt == 2:
                    raise
                time.sleep(1)
        raise RuntimeError("unreachable")

    with ThreadPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(fetch, sources))
    manifest = {
        "microsoft_version": "v1.1",
        "microsoft_revision": MS_REVISION,
        "anthropic_release": "2025-02-10",
        "anthropic_revision": hf_revision,
        "files": records,
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--anthropic-revision", required=True)
    acquire(parser.parse_args().anthropic_revision)
