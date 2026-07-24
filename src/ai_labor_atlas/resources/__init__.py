"""Packaged read-only configuration for installed Atlas distributions."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def resource_path(name: str) -> Path:
    """Return a filesystem path for a resource included in the wheel."""

    return Path(str(files(__package__).joinpath(name)))
