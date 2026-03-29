import csv
import subprocess
from pathlib import Path

import pytest

from tc_scanner_launcher import (
    DEFAULT_CONFIG,
    FolderContext,
    append_scan_log,
    cleanup_temp_file,
    collect_parse_warnings,
    format_scan_process_error,
    get_temp_output_path,
    load_config,
    move_temp_to_final,
    resolve_final_output_path,
    save_config,
    select_initial_tag,
    validate_doc_types,
    validate_temp_scan_result,
)


def test_resolve_final_output_path_overwrite(tmp_path: Path):
    target = tmp_path / "file.pdf"
    target.write_bytes(b"old")

    resolved, strategy = resolve_final_output_path(target, "overwrite")

    assert resolved == target
    assert strategy == "overwrite"


def test_resolve_final_output_path_increment(tmp_path: Path):
    target = tmp_path / "file.pdf"
    target.write_bytes(b"old")
    (tmp_path / "file (2).pdf").write_bytes(b"old2")

    resolved, strategy = resolve_final_output_path(target, "increment")

    assert resolved == tmp_path / "file (3).pdf"
    assert strategy == "increment"


def test_resolve_final_output_path_ask_cancel(tmp_path: Path):
    target = tmp_path / "file.pdf"
    target.write_bytes(b"old")

    resolved, strategy = resolve_final_output_path(target, "ask", ask_user_choice=lambda: "cancel")

    assert resolved is None
    assert strategy == "cancelled"


def test_temp_file_created_and_moved(tmp_path: Path):
    temp = tmp_path / "tmp" / "scan.pdf"
    final = tmp_path / "out" / "scan.pdf"
    temp.parent.mkdir(parents=True)
    temp.write_bytes(b"%PDF-1.7")

    validate_temp_scan_result(temp)
    moved = move_temp_to_final(temp, final)

    assert moved == final
    assert final.exists()
    assert not temp.exists()


def test_temp_file_missing_raises(tmp_path: Path):
    temp = tmp_path / "tmp" / "missing.pdf"

    with pytest.raises(FileNotFoundError):
        validate_temp_scan_result(temp)


def test_move_failure_raises(monkeypatch, tmp_path: Path):
    temp = tmp_path / "tmp" / "scan.pdf"
    final = tmp_path / "out" / "scan.pdf"
    temp.parent.mkdir(parents=True)
    temp.write_bytes(b"x")

    def fail_move(*_args, **_kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr("tc_scanner_launcher.shutil.move", fail_move)

    with pytest.raises(RuntimeError, match="Не вдалося перемістити файл"):
        move_temp_to_final(temp, final)


def test_append_scan_log_success_error_cancelled(tmp_path: Path):
    log_path = tmp_path / "scan_log.csv"
    base_entry = {
        "timestamp": "2026-03-29T00:00:00",
        "current_folder": "C:/Work",
        "document_key": "vvzv",
        "document_label": "ВВЗВ",
        "selected_tag": "СЗ",
        "generated_filename": "001_test.pdf",
        "temp_output_path": "C:/tmp/scan_tmp.pdf",
        "final_output_path": "C:/Work/001_test.pdf",
        "duplicate_strategy": "ask",
        "message": "",
    }
    append_scan_log(log_path, {**base_entry, "status": "success"})
    append_scan_log(log_path, {**base_entry, "status": "error", "message": "scan failed"})
    append_scan_log(log_path, {**base_entry, "status": "cancelled", "message": "user cancelled"})

    with log_path.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    assert [row["status"] for row in rows] == ["success", "error", "cancelled"]


def test_load_config_backwards_compatible(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "scanner_config.json"
    config_path.write_text('{"scan_command": "scanner", "doc_types": []}', encoding="utf-8")
    monkeypatch.setattr("tc_scanner_launcher.CONFIG_PATH", config_path)

    cfg = load_config()

    assert cfg["scan_command"] == "scanner"
    assert cfg["duplicate_strategy"] == DEFAULT_CONFIG["duplicate_strategy"]
    assert cfg["temp_dir"] == DEFAULT_CONFIG["temp_dir"]
    assert cfg["log_file"] == DEFAULT_CONFIG["log_file"]
    assert cfg["ui_state"]["last_doc_type"] == DEFAULT_CONFIG["ui_state"]["last_doc_type"]


def test_ui_state_load_and_save(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "scanner_config.json"
    config_path.write_text('{"scan_command":"scanner"}', encoding="utf-8")
    monkeypatch.setattr("tc_scanner_launcher.CONFIG_PATH", config_path)

    cfg = load_config()
    cfg["ui_state"] = {"last_doc_type": "as", "last_tag": "СЗ"}
    save_config(cfg)

    reloaded = load_config()
    assert reloaded["ui_state"]["last_doc_type"] == "as"
    assert reloaded["ui_state"]["last_tag"] == "СЗ"


def test_validate_doc_types_valid_and_invalid():
    valid = [{"key": "as", "label": "АС", "code": "005", "template": "{code}_{label}_{date}_{episode}_{tag}"}]
    invalid = [{"key": "as", "label": "АС", "code": "005", "template": "{code}_{unknown}"}]

    assert validate_doc_types(valid) == (True, None)
    ok, message = validate_doc_types(invalid)
    assert not ok
    assert "невідомі плейсхолдери" in message


def test_collect_parse_warnings():
    doc_with_section = {"template": "{code}_{section}_{date}_{episode}_{tag}"}
    ctx = FolderContext(date="", episode="1", tags=["СЗ"], section="")

    warnings = collect_parse_warnings(ctx, "СЗ", doc_with_section)
    assert "не знайдено дату" in warnings
    assert "не знайдено секцію" in warnings

    warnings = collect_parse_warnings(FolderContext(date="10.01.25", episode="", section="01"), "СЗ", doc_with_section)
    assert "не знайдено епізод" in warnings

    warnings = collect_parse_warnings(FolderContext(date="10.01.25", episode="1", section="01"), "", doc_with_section)
    assert "не знайдено підрозділ" in warnings


def test_select_initial_tag_autoselect_one():
    assert select_initial_tag(["СЗ"], "РС") == "СЗ"


def test_get_temp_output_path(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("tc_scanner_launcher.__file__", str(tmp_path / "tc_scanner_launcher.py"))
    path = get_temp_output_path("tmp_scans", "pdf")
    assert path.parent.name == "tmp_scans"
    assert path.suffix == ".pdf"


def test_cleanup_temp_file(tmp_path: Path):
    path = tmp_path / "tmp.pdf"
    path.write_bytes(b"1")
    cleanup_temp_file(path)
    assert not path.exists()


def test_format_scan_process_error_uses_stderr():
    err = subprocess.CalledProcessError(1, "scan", stderr="Не знайдено пристрій Pantum")
    text = format_scan_process_error(err)
    assert "Не знайдено пристрій Pantum" in text
