from __future__ import annotations

import re
from typing import Any

from app_config import NamingConfig


def sanitize_part(value: str) -> str:
    value = str(value or "").strip()
    value = re.sub(r'[\\/:*?"<>|]+', '-', value)
    value = re.sub(r'\s+', ' ', value)
    return value


def render_filename_template(template: str, values: dict[str, Any]) -> str:
    safe_values = {k: sanitize_part(v) for k, v in values.items()}
    return str(template or "").format(**safe_values)


def normalize_generated_filename(raw: str, naming: NamingConfig) -> str:
    text = str(raw or "")
    if naming.replace_spaces:
        text = text.replace(" ", naming.replace_spaces)
    if naming.trim_extra_separators:
        escaped = re.escape(naming.replace_spaces or "_")
        text = re.sub(rf"{escaped}+", naming.replace_spaces or "_", text)
        text = re.sub(r"_+", "_", text)
    text = re.sub(r"\s+", " ", text).strip("_ -.")
    if naming.max_length > 0:
        text = text[: naming.max_length].rstrip("_ -.")
    return text


def build_document_filename(template: str, minimal_template: str, values: dict[str, Any], naming: NamingConfig) -> str:
    rendered = render_filename_template(template, values)
    normalized = normalize_generated_filename(rendered, naming)
    if normalized:
        return normalized
    if naming.fallback_if_empty:
        fallback = render_filename_template(minimal_template, values)
        return normalize_generated_filename(fallback, naming)
    return ""
