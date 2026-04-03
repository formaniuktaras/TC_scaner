from __future__ import annotations

import sys
from pathlib import Path


def get_app_dir(base_file: str | Path | None = None) -> Path:
    """Return stable writable directory for both script and frozen modes."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    if base_file is None:
        base_file = __file__
    return Path(base_file).resolve().parent


def resolve_app_path(path_value: str, fallback: str, base_file: str | Path | None = None) -> Path:
    value = (path_value or fallback).strip() or fallback
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return get_app_dir(base_file) / candidate
