"""Runtime paths that work in source checkouts and installed distributions."""

from __future__ import annotations

import os
from pathlib import Path

from .resources import resource_path


SOURCE_ROOT = Path(__file__).resolve().parents[2]


def config_path(name: str) -> Path:
    """Prefer editable source config and fall back to wheel resources."""

    source_path = SOURCE_ROOT / "config" / name
    return source_path if source_path.exists() else resource_path(name)


def data_root() -> Path:
    """Resolve mutable data outside the Python installation directory."""

    configured = os.environ.get("AI_LABOR_ATLAS_DATA_DIR", "").strip()
    return (
        Path(configured).expanduser().resolve()
        if configured
        else (Path.cwd() / "data").resolve()
    )
