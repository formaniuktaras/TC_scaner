from app_config import NamingConfig
from naming_utils import build_document_filename, normalize_generated_filename


def test_normalize_generated_filename_trims_duplicates():
    naming = NamingConfig(replace_spaces="_", max_length=180, trim_extra_separators=True)
    assert normalize_generated_filename("  A  __B___  ", naming) == "A_B"


def test_empty_values_do_not_break_name():
    naming = NamingConfig()
    values = {"code": "001", "label": "АС", "date": "", "episode": "", "section": "", "tag": ""}
    name = build_document_filename("{code}_{label}_{date}_{episode}_{tag}", "{code}_{label}", values, naming)
    assert name == "001_АС"


def test_minimal_template_fallback():
    naming = NamingConfig(fallback_if_empty=True)
    values = {"code": "001", "label": "АС", "date": "", "episode": "", "section": "", "tag": ""}
    assert build_document_filename("{tag}", "{code}_{label}", values, naming) == "001_АС"


def test_max_length_trimming():
    naming = NamingConfig(max_length=10)
    out = normalize_generated_filename("1234567890123", naming)
    assert out == "1234567890"
