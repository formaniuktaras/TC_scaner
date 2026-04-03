import json
from pathlib import Path

import pytest

from app_config import AppConfig, ConfigValidationError, load_config, save_config


def test_load_default_config_creates_file(tmp_path: Path):
    cfg_path = tmp_path / "scanner_config.json"
    cfg = load_config(cfg_path)
    assert cfg_path.exists()
    assert cfg.scan.output_extension == "pdf"




def test_load_default_config_uses_template_when_present(tmp_path: Path, monkeypatch):
    cfg_path = tmp_path / "scanner_config.json"
    template = tmp_path / "scanner_config.default.json"
    template.write_text(json.dumps({"scan": {"profile_name": "CUSTOM"}}), encoding="utf-8")
    monkeypatch.setattr("app_config.get_default_config_template_path", lambda: template)

    cfg = load_config(cfg_path)

    assert cfg.scan.profile_name == "CUSTOM"
    assert cfg_path.exists()
def test_migrate_legacy_flat_config(tmp_path: Path):
    cfg_path = tmp_path / "scanner_config.json"
    cfg_path.write_text(json.dumps({"scan_command": "scanner -o \"{output_path}\"", "temp_dir": "tmp2"}), encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg.scan.command_template.startswith("scanner")
    assert cfg.scan.mode == "manual"
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


def test_profile_mode_validation(tmp_path: Path):
    cfg = AppConfig()
    cfg.scan.mode = "profile"
    cfg.scan.naps2_exe = "C:/NAPS2/NAPS2.Console.exe"
    cfg.scan.profile_name = "DR"
    save_config(cfg, tmp_path / "scanner_config.json")


def test_manual_mode_validation_requires_fields():
    cfg = AppConfig()
    cfg.scan.mode = "manual"
    cfg.scan.device = ""
    with pytest.raises(ConfigValidationError):
        cfg.validate()


def test_roundtrip_profile_and_manual_modes(tmp_path: Path):
    cfg_path = tmp_path / "scanner_config.json"
    cfg = AppConfig()
    cfg.scan.mode = "profile"
    cfg.scan.profile_name = "PROF_A"
    save_config(cfg, cfg_path)
    loaded = load_config(cfg_path)
    assert loaded.scan.mode == "profile"
    assert loaded.scan.profile_name == "PROF_A"

    loaded.scan.mode = "manual"
    loaded.scan.driver = "wia"
    loaded.scan.device = "CANON DR-C240 USB"
    save_config(loaded, cfg_path)
    loaded2 = load_config(cfg_path)
    assert loaded2.scan.mode == "manual"
    assert loaded2.scan.device == "CANON DR-C240 USB"
