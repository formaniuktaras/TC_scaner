import csv
from pathlib import Path

import pytest

from tc_scanner_launcher import (
    DEFAULT_CONFIG,
    append_scan_log,
    load_config,
    perform_scan_with_temp,
    resolve_final_output_path,
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


def test_perform_scan_with_temp_raises_when_temp_missing(tmp_path: Path, monkeypatch):
    temp_path = tmp_path / "tmp" / "scan_tmp.pdf"
    final_path = tmp_path / "out" / "file.pdf"

    monkeypatch.setattr("tc_scanner_launcher.run_scan", lambda *_args, **_kwargs: None)

    with pytest.raises(FileNotFoundError, match="Тимчасовий файл сканування не створено"):
        perform_scan_with_temp(
            cmd_template="scanner --output {output_path}",
            temp_output_path=temp_path,
            final_output_path=final_path,
        )


def test_perform_scan_with_temp_moves_to_final(tmp_path: Path, monkeypatch):
    temp_path = tmp_path / "tmp" / "scan_tmp.pdf"
    final_path = tmp_path / "out" / "file.pdf"

    def fake_run(_cmd: str, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.7 mock")

    monkeypatch.setattr("tc_scanner_launcher.run_scan", fake_run)

    result = perform_scan_with_temp(
        cmd_template="scanner --output {output_path}",
        temp_output_path=temp_path,
        final_output_path=final_path,
    )

    assert result == final_path
    assert final_path.exists()
    assert final_path.read_bytes() == b"%PDF-1.7 mock"
    assert not temp_path.exists()


def test_append_scan_log_writes_success_and_error_rows(tmp_path: Path):
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
    }
    append_scan_log(log_path, {**base_entry, "status": "success", "message": "ok"})
    append_scan_log(log_path, {**base_entry, "status": "error", "message": "fail"})

    with log_path.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == 2
    assert rows[0]["status"] == "success"
    assert rows[1]["status"] == "error"


def test_load_config_backwards_compatible(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "scanner_config.json"
    config_path.write_text('{"scan_command": "scanner", "doc_types": []}', encoding="utf-8")
    monkeypatch.setattr("tc_scanner_launcher.CONFIG_PATH", config_path)

    cfg = load_config()

    assert cfg["scan_command"] == "scanner"
    assert cfg["duplicate_strategy"] == DEFAULT_CONFIG["duplicate_strategy"]
    assert cfg["temp_dir"] == DEFAULT_CONFIG["temp_dir"]
    assert cfg["log_file"] == DEFAULT_CONFIG["log_file"]
