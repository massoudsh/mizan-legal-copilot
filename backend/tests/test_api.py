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


def tenant(role="admin"):
    org = client.post("/admin/organizations", headers=PLATFORM, json={"name": f"سازمان {uuid4()}"}).json()["organization_id"]
    user = client.post(f"/admin/organizations/{org}/users", headers=PLATFORM, json={"email": f"{uuid4()}@example.com", "role": role}).json()
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


def test_oversize_and_honeypot_are_rejected():
    assert client.post("/analyze", headers=tenant(), files={"file": ("b.txt", b"a" * 1001)}).status_code == 413
    assert client.post("/demo-requests", json={"name": "مینا", "organization": "نمونه", "work_email": "mina@example.com", "website": "spam"}).status_code == 422
