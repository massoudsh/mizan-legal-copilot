"""The API container also serves the landing page and dashboard."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["ENVIRONMENT"] = "development"
os.environ["MIZAN_API_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import LANDING_DIR, app  # noqa: E402

client = TestClient(app)


def test_landing_directory_is_discovered():
    assert LANDING_DIR is not None
    assert (LANDING_DIR / "index.html").is_file()


def test_landing_and_dashboard_are_served_from_the_root():
    landing = client.get("/")
    assert landing.status_code == 200
    assert "text/html" in landing.headers["content-type"]
    assert "/demo-requests" in landing.text

    dashboard = client.get("/dashboard.html")
    assert dashboard.status_code == 200
    assert "dashboard.js" in dashboard.text

    assert client.get("/styles.css").status_code == 200
    assert client.get("/dashboard.js").status_code == 200


def test_source_and_test_files_are_not_exposed():
    for path in ("/dashboard.test.cjs", "/README.md", "/package.json"):
        assert client.get(path).status_code == 404


def test_api_routes_win_over_the_static_mount():
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/me").status_code == 401
    assert client.post("/demo-requests", json={}).status_code == 422


def test_unknown_paths_do_not_fall_back_to_the_landing_page():
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert "<html" not in response.text.lower()


def test_security_headers_are_set_for_pages_and_api_responses():
    for path in ("/", "/health"):
        headers = client.get(path).headers
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["referrer-policy"] == "no-referrer"
        assert headers["x-frame-options"] == "DENY"
