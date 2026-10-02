import pytest

from phantomlayer_agent.client import PhantomLayerClient
from phantomlayer_agent.config import AgentSettings
from phantomlayer_agent.registration import (
    AgentRegistrationError,
    AgentRegistrationManager,
)


@pytest.mark.asyncio
async def test_registration_success():
    settings = AgentSettings(
        agent_name="test-agent",
        agent_version="0.1.0",
    )

    client = PhantomLayerClient(settings)

    async def fake_register(**kwargs):
        assert kwargs["name"] == "test-agent"
        assert kwargs["version"] == "0.1.0"
        assert kwargs["admin_access_token"] == "admin-token"
        assert kwargs["domain_id"] == "domain-test-123"
        assert "api-protection" in kwargs["capabilities"]
        assert "database-protection" in kwargs["capabilities"]
        assert "honeypot-routing" in kwargs["capabilities"]
        assert "telemetry" in kwargs["capabilities"]

        return {
            "agent_id": "agent-test-123",
            "name": "test-agent",
            "status": "pending",
            "registration_token": "registration-secret",
        }

    client.register = fake_register

    manager = AgentRegistrationManager(
        settings=settings,
        client=client,
    )

    response = await manager.register(
        admin_access_token="admin-token",
        domain_id="domain-test-123",
    )

    assert response["agent_id"] == "agent-test-123"
    assert response["registration_token"] == "registration-secret"


@pytest.mark.asyncio
async def test_registration_failure_is_wrapped():
    settings = AgentSettings()

    client = PhantomLayerClient(settings)

    async def fake_register(**kwargs):
        raise RuntimeError("connection refused")

    client.register = fake_register

    manager = AgentRegistrationManager(
        settings=settings,
        client=client,
    )

    with pytest.raises(
        AgentRegistrationError,
        match="Agent registration failed",
    ):
        await manager.register(
            admin_access_token="admin-token",
            domain_id="domain-test-123",
        )


@pytest.mark.asyncio
async def test_registration_rejects_missing_agent_id():
    settings = AgentSettings()

    client = PhantomLayerClient(settings)

    async def fake_register(**kwargs):
        return {
            "name": "test-agent",
            "status": "pending",
            "registration_token": "secret",
        }

    client.register = fake_register

    manager = AgentRegistrationManager(
        settings=settings,
        client=client,
    )

    with pytest.raises(
        AgentRegistrationError,
        match="agent_id",
    ):
        await manager.register(
            admin_access_token="admin-token",
            domain_id="domain-test-123",
        )


@pytest.mark.asyncio
async def test_registration_rejects_missing_token():
    settings = AgentSettings()

    client = PhantomLayerClient(settings)

    async def fake_register(**kwargs):
        return {
            "agent_id": "agent-test",
            "name": "test-agent",
            "status": "pending",
        }

    client.register = fake_register

    manager = AgentRegistrationManager(
        settings=settings,
        client=client,
    )

    with pytest.raises(
        AgentRegistrationError,
        match="registration_token",
    ):
        await manager.register(
            admin_access_token="admin-token",
            domain_id="domain-test-123",
        )


@pytest.mark.asyncio
async def test_registration_requires_admin_token():
    settings = AgentSettings()

    client = PhantomLayerClient(settings)

    manager = AgentRegistrationManager(
        settings=settings,
        client=client,
    )

    with pytest.raises(
        AgentRegistrationError,
        match="admin_access_token",
    ):
        await manager.register(
            domain_id="domain-test-123",
        )


@pytest.mark.asyncio
async def test_registration_fetches_verified_domain():
    settings = AgentSettings(
        agent_name="test-agent",
        agent_version="0.1.0",
    )

    client = PhantomLayerClient(settings)

    async def fake_list_domains(**kwargs):
        assert kwargs["admin_access_token"] == "admin-token"

        return [
            {
                "id": "unverified-domain",
                "domain": "unverified.example",
                "verified": False,
            },
            {
                "id": "verified-domain",
                "domain": "verified.example",
                "verified": True,
            },
        ]

    async def fake_register(**kwargs):
        assert kwargs["domain_id"] == "verified-domain"
        assert kwargs["admin_access_token"] == "admin-token"

        return {
            "agent_id": "agent-test-123",
            "name": "test-agent",
            "status": "pending",
            "registration_token": "registration-secret",
        }

    client.list_domains = fake_list_domains
    client.register = fake_register

    manager = AgentRegistrationManager(
        settings=settings,
        client=client,
    )

    response = await manager.register(
        admin_access_token="admin-token",
    )

    assert response["agent_id"] == "agent-test-123"


@pytest.mark.asyncio
async def test_registration_rejects_when_no_verified_domain_exists():
    settings = AgentSettings()

    client = PhantomLayerClient(settings)

    async def fake_list_domains(**kwargs):
        return [
            {
                "id": "unverified-domain",
                "domain": "unverified.example",
                "verified": False,
            },
        ]

    client.list_domains = fake_list_domains

    manager = AgentRegistrationManager(
        settings=settings,
        client=client,
    )

    with pytest.raises(
        AgentRegistrationError,
        match="No verified domain",
    ):
        await manager.register(
            admin_access_token="admin-token",
        )


def test_persist_credentials(tmp_path):
    settings = AgentSettings()

    client = PhantomLayerClient(settings)

    manager = AgentRegistrationManager(
        settings=settings,
        client=client,
    )

    credentials_path = tmp_path / ".agent_credentials.env"

    manager.persist_credentials(
        response={
            "agent_id": "agent-test-123",
            "registration_token": "registration-secret",
        },
        path=credentials_path,
    )

    assert credentials_path.exists()

    content = credentials_path.read_text()

    assert "AGENT_ID=agent-test-123" in content
    assert "REGISTRATION_TOKEN=registration-secret" in content

    assert credentials_path.stat().st_mode & 0o777 == 0o600