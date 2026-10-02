import pytest

from phantomlayer_agent.client import PhantomLayerClient
from phantomlayer_agent.config import AgentSettings
from phantomlayer_agent.heartbeat import HeartbeatWorker


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch):
    """
    Remove real environment variables so tests are independent
    from the developer's shell environment.

    The tests also explicitly disable .env loading when creating
    AgentSettings instances.
    """

    variables = [
        "PHANTOMLAYER_URL",
        "AGENT_ID",
        "REGISTRATION_TOKEN",
        "AGENT_NAME",
        "AGENT_VERSION",
        "HEARTBEAT_INTERVAL_SECONDS",
        "REAL_DATABASE_URL",
        "HONEYPOT_DATABASE_URL",
        "TELEMETRY_BATCH_SIZE",
    ]

    for variable in variables:
        monkeypatch.delenv(variable, raising=False)


def test_default_settings():
    settings = AgentSettings(_env_file=None)

    assert settings.phantomlayer_url == "http://localhost:8000"
    assert settings.agent_id is None
    assert settings.registration_token is None
    assert settings.agent_name == "phantomlayer-agent"
    assert settings.agent_version == "0.1.0"
    assert settings.heartbeat_interval_seconds == 30
    assert settings.real_database_url == ""
    assert settings.honeypot_database_url == ""
    assert settings.telemetry_batch_size == 20


def test_environment_settings(monkeypatch):
    monkeypatch.setenv(
        "PHANTOMLAYER_URL",
        "http://phantomlayer:8000",
    )
    monkeypatch.setenv(
        "AGENT_ID",
        "agent-test-123",
    )
    monkeypatch.setenv(
        "REGISTRATION_TOKEN",
        "secret-test-token",
    )
    monkeypatch.setenv(
        "AGENT_NAME",
        "test-agent",
    )
    monkeypatch.setenv(
        "AGENT_VERSION",
        "1.2.3",
    )
    monkeypatch.setenv(
        "HEARTBEAT_INTERVAL_SECONDS",
        "60",
    )
    monkeypatch.setenv(
        "REAL_DATABASE_URL",
        "postgresql://real-test",
    )
    monkeypatch.setenv(
        "HONEYPOT_DATABASE_URL",
        "postgresql://honeypot-test",
    )
    monkeypatch.setenv(
        "TELEMETRY_BATCH_SIZE",
        "50",
    )

    settings = AgentSettings(_env_file=None)

    assert settings.phantomlayer_url == "http://phantomlayer:8000"
    assert settings.agent_id == "agent-test-123"
    assert settings.registration_token == "secret-test-token"
    assert settings.agent_name == "test-agent"
    assert settings.agent_version == "1.2.3"
    assert settings.heartbeat_interval_seconds == 60
    assert settings.real_database_url == "postgresql://real-test"
    assert settings.honeypot_database_url == "postgresql://honeypot-test"
    assert settings.telemetry_batch_size == 50


def test_client_requires_registration_token():
    settings = AgentSettings(_env_file=None)

    client = PhantomLayerClient(settings)

    with pytest.raises(
        RuntimeError,
        match="REGISTRATION_TOKEN is not configured",
    ):
        client._headers()


def test_client_headers():
    settings = AgentSettings(
        _env_file=None,
        registration_token="test-token",
    )

    client = PhantomLayerClient(settings)

    headers = client._headers()

    assert headers["Authorization"] == "Bearer test-token"
    assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_heartbeat_requires_agent_id():
    settings = AgentSettings(
        _env_file=None,
        registration_token="test-token",
    )

    client = PhantomLayerClient(settings)

    with pytest.raises(
        RuntimeError,
        match="AGENT_ID is not configured",
    ):
        await client.heartbeat(
            status="healthy",
            real_db_reachable=True,
            honeypot_db_reachable=True,
        )


@pytest.mark.asyncio
async def test_heartbeat_worker_reports_healthy(monkeypatch):
    settings = AgentSettings(
        _env_file=None,
        agent_id="agent-test",
        registration_token="test-token",
        real_database_url="postgresql://real",
        honeypot_database_url="postgresql://honeypot",
    )

    client = PhantomLayerClient(settings)

    async def fake_check_databases(real_url, honeypot_url):
        assert real_url == "postgresql://real"
        assert honeypot_url == "postgresql://honeypot"

        return True, True

    async def fake_heartbeat(**kwargs):
        assert kwargs["status"] == "healthy"
        assert kwargs["real_db_reachable"] is True
        assert kwargs["honeypot_db_reachable"] is True
        assert kwargs["telemetry_events_sent"] == 0

        return {
            "agent_id": "agent-test",
            "status": "healthy",
        }

    monkeypatch.setattr(
        "phantomlayer_agent.heartbeat.check_databases",
        fake_check_databases,
    )

    monkeypatch.setattr(
        client,
        "heartbeat",
        fake_heartbeat,
    )

    worker = HeartbeatWorker(
        settings=settings,
        client=client,
    )

    result = await worker.send_once()

    assert result["agent_id"] == "agent-test"
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_heartbeat_worker_reports_degraded(monkeypatch):
    settings = AgentSettings(
        _env_file=None,
        agent_id="agent-test",
        registration_token="test-token",
    )

    client = PhantomLayerClient(settings)

    async def fake_check_databases(real_url, honeypot_url):
        return True, False

    captured = {}

    async def fake_heartbeat(**kwargs):
        captured.update(kwargs)

        return {
            "agent_id": "agent-test",
            "status": "degraded",
        }

    monkeypatch.setattr(
        "phantomlayer_agent.heartbeat.check_databases",
        fake_check_databases,
    )

    monkeypatch.setattr(
        client,
        "heartbeat",
        fake_heartbeat,
    )

    worker = HeartbeatWorker(
        settings=settings,
        client=client,
    )

    result = await worker.send_once()

    assert result["status"] == "degraded"
    assert captured["status"] == "degraded"


@pytest.mark.asyncio
async def test_heartbeat_worker_reports_offline(monkeypatch):
    settings = AgentSettings(
        _env_file=None,
        agent_id="agent-test",
        registration_token="test-token",
    )

    client = PhantomLayerClient(settings)

    async def fake_check_databases(real_url, honeypot_url):
        return False, False

    captured = {}

    async def fake_heartbeat(**kwargs):
        captured.update(kwargs)

        return {
            "agent_id": "agent-test",
            "status": "offline",
        }

    monkeypatch.setattr(
        "phantomlayer_agent.heartbeat.check_databases",
        fake_check_databases,
    )

    monkeypatch.setattr(
        client,
        "heartbeat",
        fake_heartbeat,
    )

    worker = HeartbeatWorker(
        settings=settings,
        client=client,
    )

    result = await worker.send_once()

    assert result["status"] == "offline"
    assert captured["status"] == "offline"