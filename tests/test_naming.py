from pathlib import Path

from tc_scanner_launcher import (
    build_filename,
    find_available_copy_path,
    missing_context_fields,
    parse_context,
    validate_doc_types,
    validate_template,
)


def test_parse_context_from_nested_folder():
    folder = Path("22005_10.05.22_1_3єб_9єр_РС+ЗББР+СЗ+ІС+ВТ/1.ЄА/01_Матеріали ЄА")
    ctx = parse_context(folder)

    assert ctx.date == "10.05.22"
    assert ctx.episode == "1"
    assert ctx.section == "01"
    assert ctx.tags == ["РС", "ЗББР", "СЗ", "ІС", "ВТ"]


def test_build_filename_extract_losses():
    folder = Path("22005_10.05.22_1_3єб_9єр_РС+ЗББР+СЗ+ІС+ВТ/1.ЄА/01_Матеріали ЄА")
    ctx = parse_context(folder)
    doc = {
        "code": "006",
        "label": "витяг з книги втрат",
        "template": "{code}_{section}_{label}_{date}_{episode}_{tag}",
    }

    assert build_filename(doc, ctx, "СЗ") == "006_01_витяг з книги втрат_10.05.22_1_СЗ"


def test_build_filename_zalyshkova_vartist():
    folder = Path("22005_10.05.22_1_3єб_9єр_РС+ЗББР+СЗ+ІС+ВТ")
    ctx = parse_context(folder)
    doc = {
        "code": "003",
        "label": "Відомість залишкової вартості",
        "template": "{code}_{label}_{date}_{episode}_{tag}",
    }

    assert build_filename(doc, ctx, "СЗ") == "003_Відомість залишкової вартості_10.05.22_1_СЗ"


def test_validate_template_with_unknown_placeholder():
    error = validate_template("{code}_{unknown}_{date}")
    assert error == "Невідомі плейсхолдери: unknown"


def test_validate_doc_types_missing_fields():
    error = validate_doc_types([{"key": "demo", "code": "001", "template": "{code}"}])
    assert "бракує полів" in (error or "")
    assert "label" in (error or "")


def test_missing_section_blocks_section_template():
    ctx = parse_context(Path("22005_10.05.22_1_3єб_9єр_РС+ЗББР+СЗ"))
    doc = {"template": "{code}_{section}_{label}_{date}_{episode}_{tag}"}
    missing = missing_context_fields(doc, ctx, "СЗ")
    assert missing == ["section"]


def test_missing_tags_blocks_tag_template():
    ctx = parse_context(Path("22005_10.05.22_1_3єб_9єр"))
    doc = {"template": "{code}_{label}_{date}_{episode}_{tag}"}
    missing = missing_context_fields(doc, ctx, "")
    assert missing == ["tag"]


def test_find_available_copy_path(tmp_path: Path):
    base = tmp_path / "scan.pdf"
    second = tmp_path / "scan (2).pdf"
    third = tmp_path / "scan (3).pdf"
    base.write_text("x", encoding="utf-8")
    second.write_text("x", encoding="utf-8")

    free_path = find_available_copy_path(base)
    assert free_path == third


def test_parse_context_with_missing_data_is_safe():
    ctx = parse_context(Path("some/random/folder"))
    assert ctx.date == ""
    assert ctx.episode == ""
    assert ctx.section == ""
    assert ctx.tags == []
