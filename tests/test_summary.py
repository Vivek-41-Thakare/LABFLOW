from types import SimpleNamespace
from app.summary import summarize
def test_critical_suppresses_ai():
    v=SimpleNamespace(critical=True,flag="CRITICAL",analyte="Potassium",value=6.8,unit="mmol/L")
    assert summarize([v])["status"]=="SUPPRESSED_CRITICAL"
def test_abnormal_has_fallback():
    v=SimpleNamespace(critical=False,flag="LOW",analyte="Hb",value=10.2,unit="g/dL")
    assert summarize([v])["status"]=="FALLBACK_TEMPLATE"


def test_locked_catalog_contains_30_templates():
    from app.summary import LOCKED_TEST_TEMPLATES
    assert len(LOCKED_TEST_TEMPLATES) == 30


def test_potassium_uses_locked_template():
    from app.summary import LOCKED_TEST_TEMPLATES
    assert "electrolyte" in LOCKED_TEST_TEMPLATES["potassium"]


def test_critical_warning_is_localized():
    v = SimpleNamespace(
        critical=True,
        flag="CRITICAL",
        analyte="Potassium",
        value=6.8,
        unit="mmol/L"
    )
    hindi = summarize([v], "hi")
    telugu = summarize([v], "te")

    assert hindi["status"] == "SUPPRESSED_CRITICAL"
    assert "गंभीर" in hindi["text"]
    assert telugu["status"] == "SUPPRESSED_CRITICAL"
    assert "ప్రయోగశాల" in telugu["text"]
