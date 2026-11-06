"""API tests for public requests and tenant-scoped operations."""

import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["ENVIRONMENT"] = "development"
os.environ["MIZAN_API_KEY"] = "test-secret-key"
os.environ["MIZAN_MAX_UPLOAD_BYTES"] = "1000"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

PLATFORM = {"X-API-Key": "test-secret-key"}
client = TestClient(app)


def tenant(role="admin", email=None):
    org = client.post("/admin/organizations", headers=PLATFORM, json={"name": f"سازمان {uuid4()}"}).json()["organization_id"]
    user = client.post(f"/admin/organizations/{org}/users", headers=PLATFORM, json={"email": email or f"{uuid4()}@example.com", "role": role}).json()
    return {"Authorization": f"Bearer {user['access_token']}"}


def test_health_ok():
    assert client.get("/health").json() == {"status": "ok"}


def test_demo_request_is_stored_without_exposing_contact_data():
    response = client.post("/demo-requests", json={"name": "مینا احمدی", "organization": "نمونه", "work_email": "mina@example.com"})
    assert response.status_code == 201
    assert set(response.json()) == {"id", "created_at"}


def test_operations_require_bearer_token():
    assert client.get("/profile").status_code == 401
    assert client.post("/analyze", files={"file": ("d.txt", b"x")}).status_code == 401


def test_tenant_profile_decisions_and_dashboard_are_isolated():
    first, second = tenant(), tenant()
    assert client.put("/profile", headers=first, json={"industry": "فناوری", "employee_count": 10}).status_code == 200
    assert client.get("/profile", headers=second).status_code == 404
    assert client.post("/decisions", headers=first, json={"title": "تصمیم", "rationale": "دلیل", "risk_level": "critical"}).status_code == 201
    assert client.get("/decisions", headers=second).json() == []
    dashboard = client.get("/dashboard", headers=first).json()
    assert dashboard["decision_count"] == 1 and dashboard["critical_decision_count"] == 1


def test_roles_limit_writes_and_analysis_uses_tenant_profile():
    viewer, analyst = tenant("viewer"), tenant("analyst")
    assert client.post("/decisions", headers=viewer, json={"title": "x", "rationale": "x"}).status_code == 403
    response = client.post("/analyze", headers=analyst, files={"file": ("contract.txt", "قرارداد پیمانکار".encode())})
    assert response.status_code == 200


def test_regulation_version_creates_alert_and_respects_dates():
    admin = tenant()
    payload = {"title": "بخشنامه مالیات", "body": "مالیات فاکتور", "source_name": "سازمان مالیات", "source_version": str(uuid4()), "effective_from": "2020-01-01"}
    assert client.post("/regulations", headers=admin, json=payload).status_code == 201
    payload["source_version"] = str(uuid4())
    assert client.post("/regulations", headers=admin, json=payload).status_code == 201
    dashboard = client.get("/dashboard", headers=admin).json()
    assert dashboard["unread_alert_count"] >= 1
    found = client.get("/regulations/search", headers=admin, params={"q": "مالیات", "on_date": "2024-01-01"})
    assert found.status_code == 200 and found.json()



def test_clm_features_cover_obligations_reviews_versions_and_audit_export():
    email = f"{uuid4()}@example.com"
    headers = tenant(email=email)
    obligation = client.post("/obligations", headers=headers, json={"title": "تمدید بیمه", "description": "ارسال مدارک", "due_on": "2027-01-10"})
    assert obligation.status_code == 201
    decision = client.post("/decisions", headers=headers, json={"title": "قرارداد", "rationale": "بررسی حقوقی"}).json()
    review = client.post("/reviews", headers=headers, json={"decision_id": decision["id"], "reviewer_email": email})
    assert review.status_code == 201
    for version, body in (("1", "بند پرداخت\nبند فسخ"), ("2", "بند پرداخت\nبند فسخ\nبند محرمانگی")):
        assert client.post("/contract-versions", headers=headers, json={"contract_key": "contract-1", "version": version, "body": body}).status_code == 201
    diff = client.get("/contract-diff", headers=headers, params={"contract_key": "contract-1", "from_version": "1", "to_version": "2"})
    assert diff.status_code == 200 and "بند محرمانگی" in diff.json()["added"]
    exported = client.get("/audit-export", headers=headers)
    assert exported.status_code == 200 and len(exported.json()["obligations"]) == 1


def test_oversize_and_honeypot_are_rejected():
    assert client.post("/demo-requests", json={"name": "مینا", "organization": "نمونه", "work_email": "mina@example.com", "website": "spam"}).status_code == 422
    assert client.post("/analyze", headers=tenant(), files={"file": ("b.txt", b"a" * 1001)}).status_code == 413


def test_review_cannot_reference_another_tenants_decision():
    first, second = tenant(), tenant()
    decision = client.post("/decisions", headers=first, json={"title": "Private", "rationale": "Private"}).json()
    for decision_id in (decision["id"], 999999):
        result = client.post("/reviews", headers=second, json={"decision_id": decision_id, "reviewer_email": "legal@example.com"})
        assert result.status_code == 404
    assert client.get("/reviews", headers=second).json() == []


def test_review_requires_assigned_reviewer_and_can_only_finish_once():
    email = f"{uuid4()}@example.com"
    headers = tenant(email=email)
    decision = client.post("/decisions", headers=headers, json={"title": "Review", "rationale": "Review"}).json()
    payload = {"decision_id": decision["id"], "reviewer_email": email}
    assert client.post("/reviews", headers=headers, json={**payload, "status": "approved"}).status_code == 422
    review = client.post("/reviews", headers=headers, json=payload).json()
    assert client.put(f"/reviews/{review['id']}", headers=tenant(), json={"status": "approved"}).status_code == 404
    response = client.put(f"/reviews/{review['id']}", headers=headers, json={"status": "approved", "note": "Checked"})
    assert response.status_code == 200 and response.json()["status"] == "approved"
    assert client.put(f"/reviews/{review['id']}", headers=headers, json={"status": "rejected"}).status_code == 409
    missing = client.post("/reviews", headers=headers, json={**payload, "reviewer_email": "missing@example.com"})
    assert missing.status_code == 404
    organization_id = client.get("/me", headers=headers).json()["organization_id"]
    other_email = f"{uuid4()}@example.com"
    client.post(f"/admin/organizations/{organization_id}/users", headers=PLATFORM, json={"email": other_email, "role": "analyst"})
    other_review = client.post("/reviews", headers=headers, json={**payload, "reviewer_email": other_email}).json()
    assert client.put(f"/reviews/{other_review['id']}", headers=headers, json={"status": "approved"}).status_code == 403


def test_obligation_updates_and_contract_diffs_are_tenant_scoped():
    first, second = tenant(), tenant()
    obligation = client.post("/obligations", headers=first, json={"title": "Duty", "description": "Task", "due_on": "2027-01-10"}).json()
    path = f"/obligations/{obligation['id']}/status"
    assert client.put(path, headers=second, json={"status": "done"}).status_code == 404
    assert client.put(path, headers=tenant("viewer"), json={"status": "done"}).status_code == 403
    assert client.put(path, headers=first, json={"status": "invalid"}).status_code == 422
    assert client.put(path, headers=first, json={"status": "done"}).json()["status"] == "done"
    version = {"contract_key": "isolated", "version": "1", "body": "Private text"}
    assert client.post("/contract-versions", headers=first, json=version).status_code == 201
    assert client.post("/contract-versions", headers=first, json=version).status_code == 409
    params = {"contract_key": "isolated", "from_version": "1", "to_version": "1"}
    assert client.get("/contract-diff", headers=second, params=params).status_code == 404
    assert client.get("/contract-diff", headers=first, params=params).json()["added"] == []
    assert client.get("/audit-export", headers=second).json()["obligations"] == []


def test_dashboard_and_audit_export_include_more_than_fifty_decisions():
    headers = tenant()
    for index in range(55):
        assert client.post("/decisions", headers=headers, json={"title": str(index), "rationale": "Audit", "risk_level": "critical"}).status_code == 201
    summary = client.get("/dashboard", headers=headers).json()
    assert summary["decision_count"] == summary["critical_decision_count"] == 55
    assert len(summary["recent_decisions"]) == 10
    assert len(client.get("/audit-export", headers=headers).json()["decisions"]) == 55
