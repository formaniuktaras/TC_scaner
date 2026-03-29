from pathlib import Path

import pytest

from app_config import AppConfig, ConfigValidationError, DocTypeConfig
from scan_runtime import build_scan_command, should_force_temp_for_path, validate_scan_config


def test_build_scan_command_substitutes_values(monkeypatch):
    cfg = AppConfig()
    cfg.scan.command_template = "scan --driver {driver} --device \"{device}\" -o \"{output_path}\""
    monkeypatch.setattr("scan_runtime.sys.platform", "win32")
    cmd = build_scan_command(cfg, Path("C:/tmp/a.pdf"))
    assert "--driver twain" in cmd
    assert '"C:/tmp/a.pdf"' in cmd


def test_command_template_validation():
    cfg = AppConfig()
    cfg.scan.command_template = "scan --driver {driver}"
    with pytest.raises(ValueError):
        validate_scan_config(cfg.scan)


def test_doc_type_template_valid_and_invalid():
    cfg = AppConfig()
    cfg.doc_types = [DocTypeConfig(key="a", label="A", code="001", template="{code}_{label}")]
    cfg.validate()
    cfg.doc_types = [DocTypeConfig(key="a", label="A", code="001", template="{unknown}")]
    with pytest.raises(ConfigValidationError):
        cfg.validate()


def test_should_force_temp_for_path_network_and_local():
    cfg = AppConfig()
    cfg.paths.network_prefixes = ["G:\\"]
    assert should_force_temp_for_path(Path("G:/docs/a.pdf"), cfg)
    assert not should_force_temp_for_path(Path("C:/docs/a.pdf"), cfg)


def test_ui_state_fields_present():
    cfg = AppConfig()
    cfg.ui_state.last_doc_type = "as"
    cfg.ui_state.last_tag = "СЗ"
    assert cfg.ui.remember_last_doc_type
    assert cfg.ui.remember_last_tag
    assert cfg.ui_state.last_doc_type == "as"
    assert cfg.ui_state.last_tag == "СЗ"
