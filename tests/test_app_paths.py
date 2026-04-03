from pathlib import Path

from app_paths import get_app_dir, get_config_path, get_log_path, get_tmp_scans_dir, resolve_app_path


def test_get_app_dir_script_mode(monkeypatch):
    monkeypatch.setattr("app_paths.sys.frozen", False, raising=False)
    monkeypatch.setattr("app_paths.APP_DIR_FALLBACK", Path("/tmp/example"))
    assert get_app_dir() == Path("/tmp/example")


def test_get_app_dir_frozen_mode(monkeypatch):
    monkeypatch.setattr("app_paths.sys.frozen", True, raising=False)
    monkeypatch.setattr("app_paths.sys.executable", "/opt/tc/TC_Scanner.exe")
    assert get_app_dir() == Path("/opt/tc")


def test_resolve_app_path_relative(monkeypatch):
    monkeypatch.setattr("app_paths.sys.frozen", False, raising=False)
    monkeypatch.setattr("app_paths.APP_DIR_FALLBACK", Path("/opt/tc"))
    result = resolve_app_path("tmp_scans", "tmp_scans")
    assert result == Path("/opt/tc/tmp_scans")


def test_resolve_app_path_absolute(monkeypatch):
    monkeypatch.setattr("app_paths.sys.frozen", False, raising=False)
    assert resolve_app_path("/tmp/scan_log.csv", "scan_log.csv") == Path("/tmp/scan_log.csv")


def test_runtime_paths_are_based_on_app_dir(monkeypatch):
    monkeypatch.setattr("app_paths.sys.frozen", False, raising=False)
    monkeypatch.setattr("app_paths.APP_DIR_FALLBACK", Path("/opt/tc"))
    assert get_config_path() == Path("/opt/tc/scanner_config.json")
    assert get_log_path() == Path("/opt/tc/scan_log.csv")
    assert get_tmp_scans_dir() == Path("/opt/tc/tmp_scans")
