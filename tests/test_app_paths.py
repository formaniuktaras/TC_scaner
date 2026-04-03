from pathlib import Path

from app_paths import get_app_dir, resolve_app_path


def test_get_app_dir_script_mode(monkeypatch):
    monkeypatch.setattr("app_paths.sys.frozen", False, raising=False)
    base = Path("/tmp/example/app_config.py")
    assert get_app_dir(base) == base.parent


def test_get_app_dir_frozen_mode(monkeypatch):
    monkeypatch.setattr("app_paths.sys.frozen", True, raising=False)
    monkeypatch.setattr("app_paths.sys.executable", "/opt/tc/TC_Scanner.exe")
    assert get_app_dir() == Path("/opt/tc")


def test_resolve_app_path_relative(monkeypatch):
    monkeypatch.setattr("app_paths.sys.frozen", False, raising=False)
    result = resolve_app_path("tmp_scans", "tmp_scans", "/opt/tc/scan_runtime.py")
    assert result == Path("/opt/tc/tmp_scans")


def test_resolve_app_path_absolute(monkeypatch):
    monkeypatch.setattr("app_paths.sys.frozen", False, raising=False)
    assert resolve_app_path("/tmp/scan_log.csv", "scan_log.csv") == Path("/tmp/scan_log.csv")
