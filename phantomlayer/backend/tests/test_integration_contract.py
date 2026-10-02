"""End-to-end trusted customer-side integration contract."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": "login-test@example.com", "password": "TestPassword123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_bank_decision_observe_routes_and_correlates_without_tenant_input():
    headers = auth_headers()
    domain = client.post(
        "/domains",
        headers=headers,
        json={"domain": f"bank-{uuid4().hex[:10]}.example.test"},
    )
    assert domain.status_code == 201
    domain_id = domain.json()["id"]
    assert client.post(f"/domains/{domain_id}/demo-verify", headers=headers).status_code == 200
    assert client.post('/protections', headers=headers, json={'domain_id': domain_id, 'layer': 'api'}).status_code == 201

    registration = client.post(
        "/agents/register",
        headers=headers,
        json={
            "name": f"bank-proxy-{uuid4().hex[:8]}",
            "domain_id": domain_id,
            "version": "test",
            "capabilities": ["bank-api", "telemetry"],
        },
    )
    assert registration.status_code == 201
    agent = registration.json()
    integration_headers = {
        "X-Agent-ID": agent["agent_id"],
        "X-Agent-Token": agent["registration_token"],
    }

    normal = client.post(
        "/integrations/bank/decision",
        headers=integration_headers,
        json={
            "session_id": str(uuid4()),
            "operation": "get_accounts",
        },
    )
    assert normal.status_code == 200
    normal_body = normal.json()
    assert normal_body["target"] == "real"
    assert "organization_id" not in normal_body
    assert client.post(
        "/integrations/bank/observe",
        headers=integration_headers,
        json={
            "decision_id": normal_body["decision_id"],
            "success": True,
            "exposed_entities": {},
            "response_count": 2,
        },
    ).status_code == 200

    suspicious = client.post(
        "/integrations/bank/decision",
        headers=integration_headers,
        json={
            "session_id": str(uuid4()),
            "operation": "enumerate_accounts",
        },
    )
    assert suspicious.status_code == 200
    suspicious_body = suspicious.json()
    assert suspicious_body["target"] == "honeypot"
    assert suspicious_body["triggered_rules"]

    observed = client.post(
        "/integrations/bank/observe",
        headers=integration_headers,
        json={
            "decision_id": suspicious_body["decision_id"],
            "success": True,
            "exposed_entities": {"accounts": 4},
            "response_count": 4,
        },
    )
    assert observed.status_code == 200

    stats = client.get("/security/stats", headers=headers)
    assert stats.status_code == 200
    assert stats.json()["total_incidents"] >= 1


def test_invalid_bank_agent_is_rejected():
    response = client.post(
        "/integrations/bank/decision",
        headers={
            "X-Agent-ID": str(uuid4()),
            "X-Agent-Token": "not-a-real-token",
        },
        json={"session_id": str(uuid4()), "operation": "get_balance"},
    )
    assert response.status_code == 401
