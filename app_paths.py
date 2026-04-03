from __future__ import annotations

import sys
from pathlib import Path


APP_DIR_FALLBACK = Path(__file__).resolve().parent


def get_app_dir() -> Path:
    """Return stable app directory for both script and frozen modes."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return APP_DIR_FALLBACK


def resolve_app_path(path_value: str, fallback: str) -> Path:
    value = (path_value or fallback).strip() or fallback
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return get_app_dir() / candidate


def get_config_path() -> Path:
    return get_app_dir() / "scanner_config.json"


def get_default_config_template_path() -> Path:
    return get_app_dir() / "scanner_config.default.json"


def get_log_path() -> Path:
    return get_app_dir() / "scan_log.csv"


def get_tmp_scans_dir() -> Path:
    return get_app_dir() / "tmp_scans"
