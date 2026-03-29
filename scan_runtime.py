from __future__ import annotations

import csv
import re
import shlex
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

from app_config import AppConfig, ScanConfig

LOG_FIELDS = [
    "timestamp",
    "status",
    "current_folder",
    "document_key",
    "document_label",
    "selected_tag",
    "generated_filename",
    "temp_output_path",
    "final_output_path",
    "duplicate_strategy",
    "message",
]


def _resolve_relative_to_launcher(path_value: str, fallback: str) -> Path:
    value = (path_value or fallback).strip() or fallback
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return Path(__file__).resolve().parent / candidate


def get_temp_dir(app_config: AppConfig) -> Path:
    path = _resolve_relative_to_launcher(app_config.paths.temp_dir, "tmp_scans")
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_log_file_path(app_config: AppConfig) -> Path:
    return _resolve_relative_to_launcher(app_config.paths.log_file, "scan_log.csv")


def normalize_output_path(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def should_force_temp_for_path(output_path: Path, app_config: AppConfig) -> bool:
    if not app_config.paths.force_temp_for_network:
        return False
    output_text = str(output_path).lower().replace("/", "\\")
    prefixes = [prefix.lower().replace("/", "\\") for prefix in app_config.paths.network_prefixes]
    return any(output_text.startswith(prefix) for prefix in prefixes)


def get_temp_output_path(app_config: AppConfig, extension: str = "pdf") -> Path:
    ext = extension.lstrip(".") or "pdf"
    temp_dir = get_temp_dir(app_config)
    return temp_dir / f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"


def validate_scan_config(scan: ScanConfig) -> None:
    if scan.command_template and "{output_path}" not in scan.command_template:
        raise ValueError("SCAN: command_template має містити {output_path}")
    if scan.mode not in {"profile", "manual"}:
        raise ValueError("SCAN: mode має бути profile/manual")


def _append_force_if_needed(cmd: str, force_overwrite_flag: bool) -> str:
    if force_overwrite_flag and "--force" not in cmd:
        return f"{cmd} --force"
    return cmd


def _format_command_template(scan: ScanConfig, output_path: Path) -> str:
    return scan.command_template.format(
        naps2_exe=scan.naps2_exe,
        profile_name=scan.profile_name,
        driver=scan.driver,
        device=scan.device,
        dpi=scan.dpi,
        page_size=scan.page_size,
        bitdepth=scan.bitdepth,
        output_path=str(output_path),
    )


def build_profile_scan_command(scan: ScanConfig, output_path: Path) -> str:
    if scan.command_template.strip():
        cmd = _format_command_template(scan, output_path)
    else:
        cmd = f'"{scan.naps2_exe}" -p "{scan.profile_name}" -o "{output_path}"'
    return _append_force_if_needed(cmd, scan.force_overwrite_flag)


def build_manual_scan_command(scan: ScanConfig, output_path: Path) -> str:
    if scan.command_template.strip():
        cmd = _format_command_template(scan, output_path)
    else:
        cmd = (
            f'"{scan.naps2_exe}" --noprofile --driver {scan.driver} --device "{scan.device}" '
            f"--pagesize {scan.page_size} --dpi {scan.dpi} --bitdepth {scan.bitdepth} -o \"{output_path}\""
        )
    return _append_force_if_needed(cmd, scan.force_overwrite_flag)


def build_scan_command(app_config: AppConfig, output_path: Path) -> str | list[str]:
    scan = app_config.scan
    validate_scan_config(scan)
    if scan.mode == "profile":
        cmd = build_profile_scan_command(scan, output_path)
    else:
        cmd = build_manual_scan_command(scan, output_path)
    if sys.platform.startswith("win"):
        return cmd
    return shlex.split(cmd, posix=True)


def run_scan(app_config: AppConfig, output_path: Path) -> None:
    args = build_scan_command(app_config, output_path)
    kwargs = {"check": True, "shell": False, "capture_output": True, "text": True}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    subprocess.run(args, **kwargs)


def validate_temp_scan_result(temp_output_path: Path) -> None:
    if not temp_output_path.exists():
        raise FileNotFoundError(f"Тимчасовий файл сканування не створено: {temp_output_path}")
    if temp_output_path.stat().st_size <= 0:
        raise ValueError(f"Тимчасовий файл сканування порожній: {temp_output_path}")


def move_temp_to_final(temp_output_path: Path, final_output_path: Path) -> Path:
    final_output_path.parent.mkdir(parents=True, exist_ok=True)
    if final_output_path.exists():
        final_output_path.unlink()
    try:
        shutil.move(str(temp_output_path), str(final_output_path))
    except Exception as exc:
        raise RuntimeError(f"Не вдалося перемістити файл у цільову папку: {exc}") from exc
    return final_output_path


def cleanup_temp_files(temp_dir: Path) -> int:
    if not temp_dir.exists():
        return 0
    removed = 0
    for item in temp_dir.iterdir():
        if item.is_file():
            item.unlink(missing_ok=True)
            removed += 1
    return removed


def cleanup_temp_file(temp_path: Path) -> None:
    if temp_path.exists():
        temp_path.unlink(missing_ok=True)


def pick_increment_path(target_path: Path) -> Path:
    if not target_path.exists():
        return target_path
    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent
    idx = 2
    while True:
        candidate = parent / f"{stem} ({idx}){suffix}"
        if not candidate.exists():
            return candidate
        idx += 1


def resolve_final_output_path(target_path: Path, duplicate_strategy: str, ask_user_choice: Callable[[], str] | None = None) -> tuple[Path | None, str]:
    strategy = (duplicate_strategy or "ask").lower()
    if strategy not in {"ask", "overwrite", "increment"}:
        strategy = "ask"
    if not target_path.exists():
        return target_path, strategy
    if strategy == "overwrite":
        return target_path, strategy
    if strategy == "increment":
        return pick_increment_path(target_path), strategy
    choice = (ask_user_choice or (lambda: "cancel"))()
    if choice == "overwrite":
        return target_path, "overwrite"
    if choice == "increment":
        return pick_increment_path(target_path), "increment"
    return None, "cancelled"


def append_scan_log(log_path: Path, entry: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = log_path.exists()
    with log_path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LOG_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow({field: entry.get(field, "") for field in LOG_FIELDS})


def format_scan_process_error(exc: subprocess.CalledProcessError) -> str:
    details = (exc.stderr or exc.stdout or "").strip()
    if details:
        return f"Сканування завершилось з помилкою (код {exc.returncode}): {details}"
    return f"Сканування завершилось з помилкою (код {exc.returncode})"
