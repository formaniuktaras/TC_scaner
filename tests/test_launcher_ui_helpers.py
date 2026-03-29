from tc_scanner_launcher import (
    FolderContext,
    collect_parse_warnings,
    format_context_line,
    format_filename_preview,
    format_scan_mode_label,
    select_initial_tag,
)
from app_config import ScanConfig


def test_select_initial_tag_uses_last_saved_value():
    assert select_initial_tag(["РС", "ВСП"], "ВСП") == "ВСП"
    assert select_initial_tag(["РС", "ВСП"], "") == "РС"
    assert select_initial_tag([], "РС") == ""


def test_formatters_for_context_and_preview():
    assert format_context_line("") == "—"
    assert format_context_line("21.07.24") == "21.07.24"
    assert format_filename_preview("  007 акт  ", "pdf") == "Файл: 007 акт.pdf"
    assert format_filename_preview("", "pdf") == "Файл: —"


def test_collect_parse_warnings_respects_missing_context():
    ctx = FolderContext(date="", episode="2осб", tags=["РС"], section="")
    warnings = collect_parse_warnings(ctx, "", "{code}_{section}_{tag}")
    assert "не знайдено підрозділ" in warnings
    assert "не знайдено дату" in warnings
    assert "не знайдено секцію" in warnings


def test_format_scan_mode_label():
    profile = ScanConfig(mode="profile", profile_name="DR")
    assert format_scan_mode_label(profile) == "Режим сканування: профіль DR"
    manual = ScanConfig(mode="manual", driver="wia", dpi=300)
    assert format_scan_mode_label(manual) == "Режим сканування: ручний (WIA / 300 dpi)"
