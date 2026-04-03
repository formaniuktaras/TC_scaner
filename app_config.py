from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app_paths import get_config_path, get_default_config_template_path

CONFIG_PATH = get_config_path()
ALLOWED_TEMPLATE_PLACEHOLDERS = {"code", "label", "date", "episode", "section", "tag"}
PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


class ConfigValidationError(ValueError):
    pass


@dataclass
class ScanConfig:
    mode: str = "profile"
    naps2_exe: str = "C:\\PROGRA~1\\NAPS2\\NAPS2.Console.exe"
    profile_name: str = "DR"
    command_template: str = ""
    driver: str = "twain"
    device: str = "Pantum"
    dpi: int = 300
    page_size: str = "a4"
    bitdepth: str = "gray"
    output_extension: str = "pdf"
    multi_page: bool = True
    force_overwrite_flag: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScanConfig":
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass
class PathsConfig:
    temp_dir: str = "tmp_scans"
    log_file: str = "scan_log.csv"
    force_temp_for_network: bool = True
    network_prefixes: list[str] = field(default_factory=lambda: ["G:\\"])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PathsConfig":
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass
class BehaviorConfig:
    duplicate_strategy: str = "ask"
    allow_incomplete_context: bool = True
    status_warnings_only: bool = True
    log_parse_warnings: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BehaviorConfig":
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass
class NamingConfig:
    fallback_if_empty: bool = True
    replace_spaces: str = "_"
    max_length: int = 180
    trim_extra_separators: bool = True
    minimal_template: str = "{code}_{label}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NamingConfig":
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass
class UiConfig:
    remember_last_doc_type: bool = True
    remember_last_tag: bool = True
    focus_name_on_start: bool = True
    show_status_bar: bool = True
    mode: str = "simple"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UiConfig":
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass
class UiStateConfig:
    last_doc_type: str = "as"
    last_tag: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UiStateConfig":
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass
class DocTypeConfig:
    key: str
    label: str
    code: str
    template: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocTypeConfig":
        return cls(
            key=str(data.get("key", "")).strip(),
            label=str(data.get("label", "")).strip(),
            code=str(data.get("code", "")).strip(),
            template=str(data.get("template", "")).strip(),
        )


DEFAULT_DOC_TYPES = [
    {"key": "vvzv", "label": "ВВЗВ", "code": "001", "template": "{code}_{label}_{date}_{episode}_{tag}"},
    {"key": "vvm", "label": "ВВМ", "code": "002", "template": "{code}_{label}_{date}_{episode}_{tag}"},
    {"key": "zalyshkova_vartist", "label": "Відомість залишкової вартості", "code": "003", "template": "{code}_{label}_{date}_{episode}_{tag}"},
    {"key": "yeas", "label": "ЄАС", "code": "004", "template": "{code}_{label}_{date}_{episode}_{tag}"},
    {"key": "as", "label": "АС", "code": "005", "template": "{code}_{label}_{date}_{episode}_{tag}"},
    {"key": "extract_losses", "label": "витяг з книги втрат", "code": "006", "template": "{code}_{section}_{label}_{date}_{episode}_{tag}"},
    {"key": "extract_shortages", "label": "витяг з книги нестач", "code": "007", "template": "{code}_{section}_{label}_{date}_{episode}_{tag}"},
    {"key": "order", "label": "Наказ", "code": "008", "template": "{code}_{label}_{date}_{episode}_{tag}"},
]


@dataclass
class AppConfig:
    scan: ScanConfig = field(default_factory=ScanConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    naming: NamingConfig = field(default_factory=NamingConfig)
    ui: UiConfig = field(default_factory=UiConfig)
    ui_state: UiStateConfig = field(default_factory=UiStateConfig)
    doc_types: list[DocTypeConfig] = field(default_factory=lambda: [DocTypeConfig.from_dict(x) for x in DEFAULT_DOC_TYPES])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        merged = merge_with_defaults(data)
        return cls(
            scan=ScanConfig.from_dict(merged["scan"]),
            paths=PathsConfig.from_dict(merged["paths"]),
            behavior=BehaviorConfig.from_dict(merged["behavior"]),
            naming=NamingConfig.from_dict(merged["naming"]),
            ui=UiConfig.from_dict(merged["ui"]),
            ui_state=UiStateConfig.from_dict(merged["ui_state"]),
            doc_types=[DocTypeConfig.from_dict(x) for x in merged["doc_types"]],
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        return result

    def validate(self) -> None:
        validate_config(self)


def default_config_dict() -> dict[str, Any]:
    return AppConfig().to_dict()


def merge_with_defaults(data: dict[str, Any] | None) -> dict[str, Any]:
    defaults = default_config_dict()
    incoming = migrate_legacy_config(data or {})
    merged = dict(defaults)
    for section in ["scan", "paths", "behavior", "naming", "ui", "ui_state"]:
        merged[section] = dict(defaults[section])
        merged[section].update(incoming.get(section, {}) or {})
    merged["doc_types"] = incoming.get("doc_types") or defaults["doc_types"]
    return merged


def _clean_scan_command(value: str) -> str:
    value = str(value or "").strip()
    value = value.replace(r'\\"{output_path}\\"', r'"{output_path}"')
    value = value.replace(r'\\"', r'\"')
    return value


def migrate_legacy_config(data: dict[str, Any]) -> dict[str, Any]:
    if "scan" in data:
        migrated = dict(data)
        if "command_template" in migrated.get("scan", {}):
            migrated["scan"]["command_template"] = _clean_scan_command(migrated["scan"].get("command_template", ""))
        if "scan_command" in migrated:
            migrated.setdefault("scan", {})
            migrated["scan"]["command_template"] = _clean_scan_command(migrated.get("scan_command", ""))
            migrated["scan"].setdefault("mode", "manual")
        return migrated

    scan_command = _clean_scan_command(data.get("scan_command", ""))
    result = default_config_dict()
    if scan_command:
        result["scan"]["command_template"] = scan_command
        result["scan"]["mode"] = "manual"
    result["scan"]["output_extension"] = data.get("output_extension", result["scan"]["output_extension"])
    result["behavior"]["duplicate_strategy"] = data.get("duplicate_strategy", result["behavior"]["duplicate_strategy"])
    result["paths"]["temp_dir"] = data.get("temp_dir", result["paths"]["temp_dir"])
    result["paths"]["log_file"] = data.get("log_file", result["paths"]["log_file"])
    result["ui_state"].update(data.get("ui_state", {}))
    if isinstance(data.get("doc_types"), list):
        result["doc_types"] = data["doc_types"]
    return result


def validate_doc_types(doc_types: list[DocTypeConfig]) -> None:
    if not isinstance(doc_types, list) or not doc_types:
        raise ConfigValidationError("doc_types має бути непорожнім списком")
    for idx, item in enumerate(doc_types, start=1):
        for field_name in ("key", "label", "code", "template"):
            if not getattr(item, field_name, "").strip():
                raise ConfigValidationError(f"DOC_TYPES: елемент #{idx} не містить '{field_name}'")
        placeholders = set(PLACEHOLDER_RE.findall(item.template))
        unknown = placeholders - ALLOWED_TEMPLATE_PLACEHOLDERS
        if unknown:
            raise ConfigValidationError(
                f"DOC_TYPES: елемент #{idx} містить невідомі плейсхолдери: {', '.join(sorted(unknown))}"
            )


def validate_config(cfg: AppConfig) -> None:
    if cfg.scan.mode not in {"profile", "manual"}:
        raise ConfigValidationError("SCAN: mode має бути profile/manual")
    if not cfg.scan.naps2_exe.strip():
        raise ConfigValidationError("SCAN: naps2_exe не може бути порожнім")
    if cfg.scan.dpi <= 0:
        raise ConfigValidationError("SCAN: dpi має бути > 0")
    if not cfg.scan.output_extension.strip():
        raise ConfigValidationError("SCAN: output_extension не може бути порожнім")
    if cfg.scan.mode == "profile":
        if not cfg.scan.profile_name.strip():
            raise ConfigValidationError("SCAN: profile_name не може бути порожнім у profile mode")
    if cfg.scan.mode == "manual":
        if not cfg.scan.driver.strip():
            raise ConfigValidationError("SCAN: driver не може бути порожнім у manual mode")
        if not cfg.scan.device.strip():
            raise ConfigValidationError("SCAN: device не може бути порожнім у manual mode")
        if not cfg.scan.page_size.strip():
            raise ConfigValidationError("SCAN: page_size не може бути порожнім у manual mode")
        if not cfg.scan.bitdepth.strip():
            raise ConfigValidationError("SCAN: bitdepth не може бути порожнім у manual mode")
    if cfg.scan.command_template and "{output_path}" not in cfg.scan.command_template:
        raise ConfigValidationError("SCAN: command_template має містити {output_path}")

    if not cfg.paths.temp_dir.strip():
        raise ConfigValidationError("PATHS: temp_dir не може бути порожнім")
    if not cfg.paths.log_file.strip():
        raise ConfigValidationError("PATHS: log_file не може бути порожнім")
    if not isinstance(cfg.paths.network_prefixes, list) or any(not isinstance(x, str) for x in cfg.paths.network_prefixes):
        raise ConfigValidationError("PATHS: network_prefixes має бути списком рядків")

    if cfg.behavior.duplicate_strategy not in {"ask", "overwrite", "increment"}:
        raise ConfigValidationError("BEHAVIOR: duplicate_strategy має бути ask/overwrite/increment")

    if cfg.naming.max_length <= 0:
        raise ConfigValidationError("NAMING: max_length має бути > 0")
    if not cfg.naming.minimal_template.strip():
        raise ConfigValidationError("NAMING: minimal_template не може бути порожнім")

    validate_doc_types(cfg.doc_types)


def _load_default_template_if_exists() -> dict[str, Any] | None:
    template_path = get_default_config_template_path()
    if not template_path.exists():
        return None
    try:
        raw = json.loads(template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigValidationError(f"Невалідний JSON у scanner_config.default.json: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigValidationError("scanner_config.default.json має містити JSON-об'єкт")
    return raw


def load_config(config_path: Path = CONFIG_PATH) -> AppConfig:
    if not config_path.exists():
        seed = _load_default_template_if_exists() or default_config_dict()
        cfg = AppConfig.from_dict(seed)
        cfg.validate()
        save_config(cfg, config_path)
        return cfg

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigValidationError(f"Невалідний JSON у config: {exc}") from exc

    cfg = AppConfig.from_dict(raw if isinstance(raw, dict) else {})
    cfg.validate()
    return cfg


def save_config(cfg: AppConfig, config_path: Path = CONFIG_PATH) -> None:
    cfg.validate()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
