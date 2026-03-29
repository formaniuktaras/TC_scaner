from pathlib import Path

from tc_scanner_launcher import _build_scan_args, build_filename, parse_context


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


def test_build_scan_args_unix_splits_and_unquotes(monkeypatch):
    monkeypatch.setattr("tc_scanner_launcher.sys.platform", "linux")
    cmd = (
        'naps2.console --driver twain --device "Pantum M6550NW" '
        '--output "{output_path}" --force'
    )

    args = _build_scan_args(cmd, Path("/tmp/test2.pdf"))

    assert args == [
        "naps2.console",
        "--driver",
        "twain",
        "--device",
        "Pantum M6550NW",
        "--output",
        "/tmp/test2.pdf",
        "--force",
    ]


def test_build_scan_args_windows_keeps_command_string(monkeypatch):
    monkeypatch.setattr("tc_scanner_launcher.sys.platform", "win32")
    cmd = (
        'C:\\PROGRA~1\\NAPS2\\NAPS2.Console.exe --driver twain --device "Pantum" '
        "-o {output_path} --force"
    )

    args = _build_scan_args(cmd, Path("C:/Temp/test 2.pdf"))

    assert isinstance(args, str)
    assert '--device "Pantum"' in args
    assert '-o "C:/Temp/test 2.pdf"' in args


def test_build_scan_args_windows_does_not_double_quote_placeholder(monkeypatch):
    monkeypatch.setattr("tc_scanner_launcher.sys.platform", "win32")
    cmd = 'scanner.exe --output "{output_path}" --force'

    args = _build_scan_args(cmd, Path("C:/Temp/test 2.pdf"))

    assert isinstance(args, str)
    assert '--output "C:/Temp/test 2.pdf"' in args


def test_parse_context_episode_with_letters_and_tags():
    folder = Path("23008_21.08.23_2осб_зрв_РС+ЗББР")
    ctx = parse_context(folder)

    assert ctx.date == "21.08.23"
    assert ctx.episode == "2осб"
    assert ctx.tags == ["РС", "ЗББР"]


def test_parse_context_episode_with_extra_parts():
    folder = Path("24007_21.07.24_1_1єб_птв_РС+СЗ+АС+ПММ")
    ctx = parse_context(folder)

    assert ctx.date == "21.07.24"
    assert ctx.episode == "1"
    assert ctx.tags == ["РС", "СЗ", "АС", "ПММ"]


def test_parse_context_without_tags():
    folder = Path("24007_21.07.24_3рв_птв")
    ctx = parse_context(folder)

    assert ctx.date == "21.07.24"
    assert ctx.episode == "3рв"
    assert ctx.tags == []


def test_parse_context_invalid_folder_does_not_crash():
    folder = Path("крива_папка")
    ctx = parse_context(folder)

    assert ctx.date == ""
    assert ctx.episode == ""
    assert ctx.tags == []
    assert ctx.section == ""


def test_parse_context_warns_on_invalid_date(caplog):
    folder = Path("23008_2023-08-21_2осб_зрв_РС+ЗББР")

    with caplog.at_level("WARNING"):
        ctx = parse_context(folder)

    assert ctx.date == "2023-08-21"
    assert ctx.episode == "2осб"
    assert any("parse_warning" in rec.message for rec in caplog.records)
