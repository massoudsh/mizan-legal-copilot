"""Regression evaluation for the deterministic risk-engine fallback."""

import json
from pathlib import Path

from app.risk_engine import _rule_based_fallback
from app.schemas import RiskLevel

ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}


def test_golden_risk_evaluations():
    cases = json.loads((Path(__file__).parents[1] / "evals" / "golden.json").read_text())
    for case in cases:
        result = _rule_based_fallback(case["name"], case["document"])
        assert ORDER[result.overall_risk_level] >= ORDER[RiskLevel(case["minimum_level"])], case["name"]
        assert any(f.requires_human_advisor for f in result.findings) is case["requires_human_advisor"], case["name"]
