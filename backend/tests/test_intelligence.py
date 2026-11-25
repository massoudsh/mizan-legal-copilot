"""Playbook, redline, Persian extraction, benchmark, and portfolio coverage."""

import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["ENVIRONMENT"] = "development"
os.environ["MIZAN_API_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PLATFORM = {"X-API-Key": "test-secret-key"}
client = TestClient(app)

CONTRACT = """قرارداد شماره: ۱۴۰۳/۱۸۷۲
طرف اول: شرکت آلفا
طرف دوم: شرکت بتا
مبلغ کل قرارداد ۲۵۰ میلیون ریال
تاریخ پایان ۱۴۰۴/۰۶/۳۱
مدت قرارداد ۱۲ ماه
این بند بدون هیچ محدودیت مسئولیت تنظیم شده است.
شرایط پرداخت: پرداخت مرحله‌ای با مهلت مشخص است.
قانون حاکم: قوانین جمهوری اسلامی ایران است.
"""


def tenant(role="admin"):
    org = client.post("/admin/organizations", headers=PLATFORM, json={"name": f"سازمان {uuid4()}"}).json()["organization_id"]
    user = client.post(f"/admin/organizations/{org}/users", headers=PLATFORM, json={"email": f"{uuid4()}@example.com", "role": role}).json()
    return {"Authorization": f"Bearer {user['access_token']}"}


def stored_contract(headers, body=CONTRACT, key="c-1", version="1"):
    response = client.post("/contract-versions", headers=headers, json={"contract_key": key, "version": version, "body": body})
    assert response.status_code == 201
    return key


def test_playbook_detects_forbidden_and_missing_clauses_with_redlines():
    admin = tenant()
    assert client.post("/clause-rules", headers=admin, json={
        "clause_key": "limitation-of-liability", "label": "مسئولیت", "severity": "high",
        "forbidden_terms": ["بدون هیچ محدودیت"], "preferred_text": "مسئولیت طرفین به مبلغ قرارداد محدود است.",
    }).status_code == 200
    assert client.post("/clause-rules", headers=admin, json={
        "clause_key": "data-protection", "label": "حفاظت داده", "severity": "medium",
        "required_terms": ["حفاظت داده"], "preferred_text": "طرفین داده‌های شخصی را طبق قانون حفاظت می‌کنند.",
    }).status_code == 200
    key = stored_contract(admin)
    review = client.post(f"/contracts/{key}/review", headers=admin, params={"version": "1"})
    assert review.status_code == 200
    body = review.json()
    kinds = {item["kind"] for item in body["deviations"]}
    assert kinds == {"forbidden", "missing"}
    assert {item["action"] for item in body["redlines"]} == {"replace", "insert"}
    assert body["score"] == 100 - (20 + 10)


def test_playbook_rules_are_tenant_scoped_and_replaceable():
    first, second = tenant(), tenant()
    rule = {"clause_key": "termination", "label": "فسخ", "forbidden_terms": ["فسخ فوری"], "severity": "high"}
    assert client.post("/clause-rules", headers=first, json=rule).json()["id"] > 0
    updated = client.post("/clause-rules", headers=first, json={**rule, "label": "فسخ قرارداد"}).json()
    assert updated["label"] == "فسخ قرارداد"
    assert len(client.get("/clause-rules", headers=first).json()) == 1
    assert client.get("/clause-rules", headers=second).json() == []
    rule_id = client.post("/clause-rules", headers=second, json={**rule, "clause_key": "payment"}).json()["id"]
    assert rule_id != updated["id"]
    assert client.delete("/clause-rules/termination", headers=first).status_code == 204
    assert client.delete("/clause-rules/termination", headers=first).status_code == 404


def test_viewers_cannot_change_the_playbook():
    viewer = tenant("viewer")
    assert client.post("/clause-rules", headers=viewer, json={"clause_key": "x", "label": "X"}).status_code == 403


def test_persian_field_extraction_normalizes_digits_and_reports_confidence():
    headers = tenant()
    key = stored_contract(headers)
    fields = client.post(f"/contracts/{key}/review", headers=headers, params={"version": "1"}).json()["fields"]
    by_key = {}
    for field in fields:
        by_key.setdefault(field["key"], []).append(field)
    amounts = by_key["amount"][0]
    assert amounts["value"].startswith("250000000"), amounts
    assert by_key["contract_number"][0]["value"] == "1403/1872"
    assert by_key["end_date"][0]["value"] == "1404/06/31"
    assert by_key["duration"][0]["value"] == "12 ماه"
    parties = {field["label"] for field in by_key["party"]}
    assert {"طرف اول", "طرف دوم"} <= parties
    assert all(0 <= field["confidence"] <= 1 for field in fields)


def test_extraction_does_not_fabricate_missing_fields():
    headers = tenant()
    key = stored_contract(headers, body="این قرارداد بدون هیچ جزئیات مالی است.")
    fields = client.post(f"/contracts/{key}/review", headers=headers, params={"version": "1"}).json()["fields"]
    assert not any(field["key"] in {"amount", "national_id", "contract_number"} for field in fields)


def test_benchmark_marks_present_and_missing_clauses():
    headers = tenant()
    key = stored_contract(headers)
    rows = client.post(f"/contracts/{key}/benchmark", headers=headers, params={"version": "1"}).json()
    statuses = {row["clause_key"]: row["status"] for row in rows}
    assert statuses["payment-terms"] == "present"
    assert statuses["force-majeure"] == "missing"
    assert all(0 <= row["frequency_pct"] <= 100 for row in rows)
    assert all(row["source"] for row in rows)


def test_portfolio_aggregates_versions_reviews_and_overdue_items():
    headers = tenant()
    stored_contract(headers, version="1")
    stored_contract(headers, version="2")
    decision = client.post("/decisions", headers=headers, json={"title": "تصمیم", "rationale": "دلیل"}).json()
    client.post("/reviews", headers=headers, json={"decision_id": decision["id"], "reviewer_email": client.get("/me", headers=headers).json()["email"]})
    client.post("/obligations", headers=headers, json={"title": "قدیمی", "description": "کار", "due_on": "2020-01-01"})
    portfolio = client.get("/portfolio", headers=headers).json()
    assert portfolio["contract_count"] == 1
    assert portfolio["version_count"] == 2
    assert portfolio["contracts"][0]["latest_version"] == "2"
    assert portfolio["pending_reviews"] == 1
    assert portfolio["overdue_obligations"] == 1


def test_review_and_benchmark_are_tenant_scoped_and_404_unknown_versions():
    first, second = tenant(), tenant()
    key = stored_contract(first)
    assert client.post(f"/contracts/{key}/review", headers=second, params={"version": "1"}).status_code == 404
    assert client.post(f"/contracts/{key}/benchmark", headers=second, params={"version": "1"}).status_code == 404
    assert client.post(f"/contracts/{key}/review", headers=first, params={"version": "99"}).status_code == 404
