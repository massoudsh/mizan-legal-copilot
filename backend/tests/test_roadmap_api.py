"""Connector configuration tests."""

from test_api import client, tenant


def test_connector_is_tenant_scoped_and_never_returns_a_secret_value():
    first, second = tenant(), tenant()
    response = client.post(
        "/connectors",
        headers=first,
        json={"name": "HR داخلی", "kind": "hr", "base_url": "https://hr.example.com/api", "secret_reference": "vault://mizan/hr-token"},
    )
    assert response.status_code == 201
    connector = response.json()
    assert connector["secret_reference"] == "vault://mizan/hr-token"
    assert client.get("/connectors", headers=second).json() == []
