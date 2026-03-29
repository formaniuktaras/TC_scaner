from pathlib import Path

import pytest

from app_config import AppConfig, ConfigValidationError, DocTypeConfig
from scan_runtime import (
    build_manual_scan_command,
    build_profile_scan_command,
    build_scan_command,
    should_force_temp_for_path,
    validate_scan_config,
)


def test_build_scan_command_profile(monkeypatch):
    cfg = AppConfig()
    cfg.scan.mode = "profile"
    cfg.scan.naps2_exe = "C:/NAPS2/NAPS2.Console.exe"
    cfg.scan.profile_name = "DR"
    monkeypatch.setattr("scan_runtime.sys.platform", "win32")
    cmd = build_scan_command(cfg, Path("C:/tmp/a.pdf"))
    assert '-p "DR"' in cmd
    assert '"C:/tmp/a.pdf"' in cmd


def test_build_scan_command_manual(monkeypatch):
    cfg = AppConfig()
    cfg.scan.mode = "manual"
    cfg.scan.driver = "wia"
    cfg.scan.device = "CANON"
    monkeypatch.setattr("scan_runtime.sys.platform", "win32")
    cmd = build_scan_command(cfg, Path("C:/tmp/a.pdf"))
    assert "--noprofile" in cmd
    assert "--driver wia" in cmd
    assert '--device "CANON"' in cmd


def test_command_template_validation_only_when_set():
    cfg = AppConfig()
    cfg.scan.command_template = "scan --driver {driver}"
    with pytest.raises(ValueError):
        validate_scan_config(cfg.scan)
    cfg.scan.command_template = ""
    validate_scan_config(cfg.scan)


def test_explicit_command_builders():
    cfg = AppConfig().scan
    manual_cmd = build_manual_scan_command(cfg, Path("C:/tmp/a.pdf"))
    assert "--noprofile" in manual_cmd
    profile_cmd = build_profile_scan_command(cfg, Path("C:/tmp/a.pdf"))
    assert '-p "DR"' in profile_cmd


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
