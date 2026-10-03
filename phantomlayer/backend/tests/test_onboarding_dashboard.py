from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import settings
from app.domains.service import DomainService
from app.main import app
from tests.dns_proof import verify_dns


client = TestClient(app)


def _login() -> str:
    response = client.post(
        "/auth/login",
        json={
            "email": "login-test@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_login()}",
    }


def _create_domain(
    domain: str | None = None,
) -> dict:
    headers = _auth_headers()

    if domain is None:
        domain = (
            f"test-{uuid4().hex[:8]}.example.com"
        )

    response = client.post(
        "/domains",
        json={
            "domain": domain,
        },
        headers=headers,
    )

    assert response.status_code == 201

    return response.json()


def _create_verified_domain() -> dict:
    domain = _create_domain()
    verify_dns(client, domain, _auth_headers())
    return domain


def test_domain_normalization():
    service = DomainService()

    assert (
        service.normalize_domain("Example.COM")
        == "example.com"
    )

    assert (
        service.normalize_domain(" Example.COM. ")
        == "example.com"
    )


def test_domain_creation():
    domain = _create_domain()

    assert domain["domain"].endswith(
        ".example.com"
    )

    assert domain["verified"] is False

    assert domain["verification_token"]

    assert domain[
        "verification_record_name"
    ].startswith(
        "_phantomlayer-verification."
    )

    assert domain["token_expires_at"]


def test_demo_domain_verification():
    domain = _create_domain()

    headers = _auth_headers()

    response = client.post(
        f"/domains/{domain['id']}/demo-verify",
        headers=headers,
    )

    assert response.status_code == 403  # Arbitrary domains always require DNS.


def test_already_verified_domain():
    domain = _create_verified_domain()

    headers = _auth_headers()

    response = client.post(
        f"/domains/{domain['id']}/verify",
        headers=headers,
    )

    if settings.demo_mode:
        assert response.status_code == 200

        payload = response.json()

        assert payload["verified"] is True
        assert payload["detail"] == (
            "Domain is already verified"
        )


def test_domain_list_is_available():
    headers = _auth_headers()

    response = client.get(
        "/domains",
        headers=headers,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_domain_get_is_available():
    domain = _create_domain()

    headers = _auth_headers()

    response = client.get(
        f"/domains/{domain['id']}",
        headers=headers,
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["id"] == domain["id"]
    assert payload["domain"] == domain["domain"]


def test_domain_get_rejects_unknown_domain():
    headers = _auth_headers()

    response = client.get(
        f"/domains/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404


def test_api_domain_url_behavior():
    """
    URL-shaped values are not DNS hostnames and must never become
    ownership challenges. Valid normalized DNS hostnames remain supported.
    """

    headers = _auth_headers()

    domain_value = (
        f"https://example-{uuid4().hex[:8]}.com/path"
    )

    response = client.post(
        "/domains",
        json={
            "domain": domain_value,
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert 'DNS hostname' in response.json()['detail']


def test_agent_registration_requires_verified_domain():
    headers = _auth_headers()

    domain = _create_domain()

    response = client.post(
        "/agents/register",
        json={
            "name": f"unverified-{uuid4().hex[:8]}",
            "domain_id": domain["id"],
            "version": "0.1.0",
            "capabilities": ["telemetry"],
        },
        headers=headers,
    )

    assert response.status_code == 422

    assert (
        response.json()["detail"]
        == "Domain must be verified before "
        "registering an agent"
    )


def test_agent_registration_and_authenticated_heartbeat():
    headers = _auth_headers()

    domain = _create_verified_domain()

    agent_name = (
        f"test-agent-{uuid4().hex[:8]}"
    )

    registration_response = client.post(
        "/agents/register",
        json={
            "name": agent_name,
            "domain_id": domain["id"],
            "version": "0.1.0",
            "capabilities": [
                "api-protection",
                "database-protection",
                "honeypot-routing",
                "telemetry",
            ],
        },
        headers=headers,
    )

    assert registration_response.status_code == 201

    registration = registration_response.json()

    assert registration["name"] == agent_name
    assert registration["status"] == "pending"
    assert registration["registration_token"]

    agent_id = registration["agent_id"]
    agent_token = registration[
        "registration_token"
    ]

    heartbeat_response = client.post(
        f"/agents/{agent_id}/heartbeat",
        json={
            "status": "healthy",
            "real_db_reachable": True,
            "honeypot_db_reachable": True,
            "telemetry_events_sent": 5,
        },
        headers={
            "X-Agent-Token": agent_token,
        },
    )

    assert heartbeat_response.status_code == 200

    heartbeat = heartbeat_response.json()

    assert heartbeat["agent_id"] == agent_id
    assert heartbeat["name"] == agent_name
    assert heartbeat["status"] == "healthy"
    assert heartbeat["real_db_reachable"] is True
    assert heartbeat[
        "honeypot_db_reachable"
    ] is True
    assert heartbeat[
        "telemetry_events_sent"
    ] == 5


def test_agent_registration_rejects_duplicate_name():
    headers = _auth_headers()

    domain = _create_verified_domain()

    agent_name = (
        f"duplicate-agent-{uuid4().hex[:8]}"
    )

    first_response = client.post(
        "/agents/register",
        json={
            "name": agent_name,
            "domain_id": domain["id"],
            "version": "0.1.0",
            "capabilities": ["telemetry"],
        },
        headers=headers,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/agents/register",
        json={
            "name": agent_name,
            "domain_id": domain["id"],
            "version": "0.1.0",
            "capabilities": ["telemetry"],
        },
        headers=headers,
    )

    assert second_response.status_code == 422

    assert (
        second_response.json()["detail"]
        == "An agent with this name already exists "
        "for this domain"
    )


def test_agent_heartbeat_rejects_missing_token():
    headers = _auth_headers()

    domain = _create_verified_domain()

    registration_response = client.post(
        "/agents/register",
        json={
            "name": (
                f"missing-token-{uuid4().hex[:8]}"
            ),
            "domain_id": domain["id"],
            "version": "0.1.0",
            "capabilities": ["telemetry"],
        },
        headers=headers,
    )

    assert registration_response.status_code == 201

    agent_id = registration_response.json()[
        "agent_id"
    ]

    heartbeat_response = client.post(
        f"/agents/{agent_id}/heartbeat",
        json={
            "status": "healthy",
            "real_db_reachable": True,
            "honeypot_db_reachable": True,
            "telemetry_events_sent": 1,
        },
    )

    assert heartbeat_response.status_code == 401

    assert (
        heartbeat_response.json()["detail"]
        == "Missing agent token"
    )


def test_agent_heartbeat_rejects_invalid_token():
    headers = _auth_headers()

    domain = _create_verified_domain()

    registration_response = client.post(
        "/agents/register",
        json={
            "name": (
                f"invalid-token-{uuid4().hex[:8]}"
            ),
            "domain_id": domain["id"],
            "version": "0.1.0",
            "capabilities": ["telemetry"],
        },
        headers=headers,
    )

    assert registration_response.status_code == 201

    agent_id = registration_response.json()[
        "agent_id"
    ]

    heartbeat_response = client.post(
        f"/agents/{agent_id}/heartbeat",
        json={
            "status": "healthy",
            "real_db_reachable": True,
            "honeypot_db_reachable": True,
            "telemetry_events_sent": 1,
        },
        headers={
            "X-Agent-Token": "definitely-invalid-token",
        },
    )

    assert heartbeat_response.status_code == 401

    assert (
        heartbeat_response.json()["detail"]
        == "Invalid agent credentials"
    )


def test_agent_token_rotation():
    headers = _auth_headers()

    domain = _create_verified_domain()

    registration_response = client.post(
        "/agents/register",
        json={
            "name": (
                f"rotate-agent-{uuid4().hex[:8]}"
            ),
            "domain_id": domain["id"],
            "version": "0.1.0",
            "capabilities": ["telemetry"],
        },
        headers=headers,
    )

    assert registration_response.status_code == 201

    registration = registration_response.json()

    agent_id = registration["agent_id"]

    old_token = registration[
        "registration_token"
    ]

    rotation_response = client.post(
        f"/agents/{agent_id}/rotate-token",
        headers=headers,
    )

    assert rotation_response.status_code == 200

    rotated = rotation_response.json()

    assert rotated["agent_id"] == agent_id

    assert rotated["registration_token"]

    assert (
        rotated["registration_token"]
        != old_token
    )

    heartbeat_payload = {
        "status": "healthy",
        "real_db_reachable": True,
        "honeypot_db_reachable": True,
        "telemetry_events_sent": 1,
    }

    old_token_response = client.post(
        f"/agents/{agent_id}/heartbeat",
        json=heartbeat_payload,
        headers={
            "X-Agent-Token": old_token,
        },
    )

    assert old_token_response.status_code == 401

    new_token_response = client.post(
        f"/agents/{agent_id}/heartbeat",
        json=heartbeat_payload,
        headers={
            "X-Agent-Token": rotated[
                "registration_token"
            ],
        },
    )

    assert new_token_response.status_code == 200


def test_agent_get_is_available():
    headers = _auth_headers()

    domain = _create_verified_domain()

    registration_response = client.post(
        "/agents/register",
        json={
            "name": (
                f"get-agent-{uuid4().hex[:8]}"
            ),
            "domain_id": domain["id"],
            "version": "0.1.0",
            "capabilities": ["telemetry"],
        },
        headers=headers,
    )

    assert registration_response.status_code == 201

    agent_id = registration_response.json()[
        "agent_id"
    ]

    response = client.get(
        f"/agents/{agent_id}",
        headers=headers,
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["agent_id"] == agent_id
    assert payload["domain_id"] == domain["id"]


def test_agent_listing_is_available():
    headers = _auth_headers()

    response = client.get(
        "/agents",
        headers=headers,
    )

    assert response.status_code == 200

    payload = response.json()

    assert isinstance(payload, list)

    for agent in payload:
        assert "agent_id" in agent
        assert "name" in agent
        assert "domain_id" in agent
        assert "status" in agent


def test_dashboard_stats_are_available():
    headers = _auth_headers()

    response = client.get(
        "/security/stats",
        headers=headers,
    )

    assert response.status_code == 200

    payload = response.json()

    assert isinstance(payload, dict)


def test_dashboard_incidents_are_available():
    headers = _auth_headers()

    response = client.get(
        "/incidents",
        headers=headers,
    )

    assert response.status_code == 200

    payload = response.json()

    assert isinstance(payload, dict)


def test_dashboard_security_events_are_available():
    headers = _auth_headers()

    response = client.get(
        "/security/events",
        headers=headers,
    )

    assert response.status_code == 200

    payload = response.json()

    assert isinstance(payload, dict)


def test_agent_registration_without_domain():
    headers = _auth_headers()

    response = client.post(
        "/agents/register",
        json={
            "name": (
                f"no-domain-{uuid4().hex[:8]}"
            ),
            "domain_id": None,
            "version": "0.1.0",
            "capabilities": ["telemetry"],
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_domain_requires_authentication():
    response = client.get("/domains")

    assert response.status_code == 401


def test_agents_require_authentication():
    response = client.get("/agents")

    assert response.status_code == 401


def test_dashboard_requires_authentication():
    response = client.get("/security/stats")

    assert response.status_code == 401
