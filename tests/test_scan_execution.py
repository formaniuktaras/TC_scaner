import sys
import threading
import time
from pathlib import Path

from tc_scanner_launcher import run_scan, wait_for_output_file


def test_run_scan_success_but_file_missing(tmp_path):
    output_path = tmp_path / "missing.pdf"
    cmd = (
        f'"{sys.executable}" -c "print(\'ok\')" '
        "--output {output_path}"
    )

    result = run_scan(cmd, output_path)

    assert result.returncode == 0
    assert result.error_type is None
    assert result.file_exists is False
    assert result.file_size == 0


def test_wait_for_output_file_detects_delayed_file(tmp_path):
    output_path = tmp_path / "delayed.pdf"

    def writer() -> None:
        time.sleep(0.4)
        output_path.write_bytes(b"abc")

    thread = threading.Thread(target=writer)
    thread.start()
    found, size = wait_for_output_file(output_path, timeout=3.0, poll_interval=0.2)
    thread.join()

    assert found is True
    assert size == 3


def test_wait_for_output_file_immediate_nonzero_file(tmp_path):
    output_path = tmp_path / "ready.pdf"
    output_path.write_bytes(b"hello")

    found, size = wait_for_output_file(output_path, timeout=2.0, poll_interval=0.2)

    assert found is True
    assert size == 5
