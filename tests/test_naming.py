from pathlib import Path

from tc_scanner_launcher import build_filename, parse_context


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
