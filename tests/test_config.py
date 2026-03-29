import json
from pathlib import Path

import pytest

from app_config import AppConfig, ConfigValidationError, load_config, save_config


def test_load_default_config_creates_file(tmp_path: Path):
    cfg_path = tmp_path / "scanner_config.json"
    cfg = load_config(cfg_path)
    assert cfg_path.exists()
    assert cfg.scan.output_extension == "pdf"


def test_migrate_legacy_flat_config(tmp_path: Path):
    cfg_path = tmp_path / "scanner_config.json"
    cfg_path.write_text(json.dumps({"scan_command": "scanner -o \"{output_path}\"", "temp_dir": "tmp2"}), encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg.scan.command_template.startswith("scanner")
    assert cfg.paths.temp_dir == "tmp2"


def test_missing_sections_filled_with_defaults(tmp_path: Path):
    cfg_path = tmp_path / "scanner_config.json"
    cfg_path.write_text(json.dumps({"scan": {"driver": "twain"}}), encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg.paths.log_file == "scan_log.csv"
    assert cfg.scan.driver == "twain"


def test_invalid_config_validation_error(tmp_path: Path):
    cfg_path = tmp_path / "scanner_config.json"
    cfg_path.write_text(json.dumps({"scan": {"dpi": -1}}), encoding="utf-8")
    with pytest.raises(ConfigValidationError):
        load_config(cfg_path)


def test_save_reload_roundtrip(tmp_path: Path):
    cfg_path = tmp_path / "scanner_config.json"
    cfg = AppConfig()
    cfg.ui_state.last_doc_type = "vvzv"
    save_config(cfg, cfg_path)
    reloaded = load_config(cfg_path)
    assert reloaded.ui_state.last_doc_type == "vvzv"
