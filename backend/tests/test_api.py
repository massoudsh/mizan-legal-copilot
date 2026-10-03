"""تست‌های endpoint های API: /health و /analyze (مسیرهای 401/400/413/422/200)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# باید قبل از import شدن app.main تنظیم شوند چون این متغیرها در سطح ماژول خوانده می‌شوند.
os.environ["ENVIRONMENT"] = "development"
os.environ["MIZAN_API_KEY"] = "test-secret-key"
os.environ["MIZAN_MAX_UPLOAD_BYTES"] = "1000"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import MAX_UPLOAD_BYTES, app  # noqa: E402

client = TestClient(app)

VALID_HEADERS = {"X-API-Key": "test-secret-key"}


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_analyze_without_api_key_returns_401():
    resp = client.post("/analyze", files={"file": ("doc.txt", b"some content", "text/plain")})
    assert resp.status_code == 401


def test_analyze_with_wrong_api_key_returns_401():
    resp = client.post(
        "/analyze",
        headers={"X-API-Key": "wrong-key"},
        files={"file": ("doc.txt", b"some content", "text/plain")},
    )
    assert resp.status_code == 401


def test_analyze_empty_file_returns_400():
    resp = client.post(
        "/analyze",
        headers=VALID_HEADERS,
        files={"file": ("doc.txt", b"", "text/plain")},
    )
    assert resp.status_code == 400


def test_analyze_unsupported_extension_returns_400():
    resp = client.post(
        "/analyze",
        headers=VALID_HEADERS,
        files={"file": ("doc.xyz", b"some content", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_analyze_oversized_file_returns_413():
    oversized = b"a" * (MAX_UPLOAD_BYTES + 1)
    resp = client.post(
        "/analyze",
        headers=VALID_HEADERS,
        files={"file": ("big.txt", oversized, "text/plain")},
    )
    assert resp.status_code == 413


def test_analyze_whitespace_only_file_returns_422():
    resp = client.post(
        "/analyze",
        headers=VALID_HEADERS,
        files={"file": ("doc.txt", b"   \n\t  ", "text/plain")},
    )
    assert resp.status_code == 422


def test_analyze_success_returns_200():
    resp = client.post(
        "/analyze",
        headers=VALID_HEADERS,
        files={"file": ("contract.txt", "این قرارداد پیمانکاری است.".encode("utf-8"), "text/plain")},
        data={"industry": "فناوری اطلاعات", "employee_count": "10"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["analysis_mode"] == "rule_fallback"
    assert body["document_name"] == "contract.txt"
    assert "findings" in body
