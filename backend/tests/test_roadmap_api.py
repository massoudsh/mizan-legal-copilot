"""تست‌های پروفایل سازمان، دفتر تصمیم، پایگاه دانش مقررات و داشبورد."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENVIRONMENT"] = "development"
os.environ["MIZAN_API_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

HEADERS = {"X-API-Key": "test-secret-key"}


def _client():
    return TestClient(app)


def test_profile_is_persisted_and_updated():
    with _client() as client:
        payload = {"organization_id": "org-1", "industry": "IT", "employee_count": 10}
        assert client.put("/organizations/profile", headers=HEADERS, json=payload).status_code == 200
        payload["employee_count"] = 25
        client.put("/organizations/profile", headers=HEADERS, json=payload)
        body = client.get("/organizations/org-1/profile", headers=HEADERS).json()
        assert body["employee_count"] == 25
        assert client.get("/organizations/unknown/profile", headers=HEADERS).status_code == 404


def test_endpoints_require_api_key():
    with _client() as client:
        assert client.get("/organizations/org-1/dashboard").status_code == 401
        assert client.post("/decisions", json={}).status_code == 401


def test_decision_log_and_dashboard():
    with _client() as client:
        for level in ("critical", "low", "low"):
            resp = client.post(
                "/decisions",
                headers=HEADERS,
                json={"organization_id": "org-2", "title": "تصمیم", "rationale": "دلیل", "risk_level": level},
            )
            assert resp.status_code == 201
        dashboard = client.get("/organizations/org-2/dashboard", headers=HEADERS).json()
        assert dashboard["decision_count"] == 3
        assert dashboard["critical_decision_count"] == 1
        assert dashboard["risk_distribution"]["low"] == 2
        assert len(client.get("/organizations/org-2/decisions", headers=HEADERS).json()) == 3


def test_regulation_search_respects_effective_dates():
    with _client() as client:
        client.post(
            "/regulations",
            headers=HEADERS,
            json={"title": "بخشنامه مالیات", "body": "مالیات ارزش افزوده فاکتور", "effective_from": "2030-01-01"},
        )
        client.post(
            "/regulations",
            headers=HEADERS,
            json={"title": "دستورالعمل بیمه", "body": "بیمه پیمانکار تأمین", "effective_to": "2000-01-01"},
        )
        client.post(
            "/regulations",
            headers=HEADERS,
            json={"title": "قانون کار", "body": "پیمانکار رابطه کار", "effective_from": "2020-01-01"},
        )
        found = client.get("/regulations/search", headers=HEADERS, params={"q": "پیمانکار", "on_date": "2024-01-01"}).json()
        assert [r["title"] for r in found] == ["قانون کار"]


def test_regulation_search_handles_special_characters():
    with _client() as client:
        resp = client.get("/regulations/search", headers=HEADERS, params={"q": '"AND OR ( * NEAR'})
        assert resp.status_code == 200


def test_analyze_uses_stored_profile_and_scanned_input_is_rejected_cleanly():
    with _client() as client:
        client.put("/organizations/profile", headers=HEADERS, json={"organization_id": "org-3", "industry": "ساخت"})
        resp = client.post(
            "/analyze",
            headers=HEADERS,
            files={"file": ("c.txt", "قرارداد پیمانکار".encode(), "text/plain")},
            data={"organization_id": "org-3"},
        )
        assert resp.status_code == 200
        blank = client.post(
            "/analyze",
            headers=HEADERS,
            files={"file": ("scan.png", b"not-an-image", "image/png")},
        )
        assert blank.status_code == 422
