"""تست‌های حالت fallback موتور ریسک (بدون نیاز به LLM_API_KEY)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.risk_engine import analyze_document
from app.schemas import OrgProfile, RiskLevel


def test_fallback_flags_labor_and_contractual_risk():
    text = "این قرارداد پیمانکاری بین طرفین منعقد می‌شود. در صورت فسخ، جریمه تعیین می‌گردد."
    result = analyze_document("contract.txt", text, OrgProfile())

    assert result.analysis_mode == "rule_fallback"
    categories = {f.category for f in result.findings}
    assert "labor" in categories
    assert "contractual" in categories
    assert result.overall_risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}


def test_fallback_no_risk_for_clean_text():
    result = analyze_document("note.txt", "این یک یادداشت داخلی ساده بدون موضوع حقوقی است.", OrgProfile())

    assert result.analysis_mode == "rule_fallback"
    assert result.findings == []
    assert result.overall_risk_level == RiskLevel.LOW
