from __future__ import annotations

import os
from pathlib import Path
import tempfile

# These values are set before importing app.main, so tests do not need PostgreSQL,
# PhantomLayer, or a developer's .env file.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="phantombank-tests-"))
os.environ.update(
    {
        "REAL_DATABASE_URL": f"sqlite:///{_TEST_DIR / 'real.db'}",
        "HONEYPOT_DATABASE_URL": f"sqlite:///{_TEST_DIR / 'honeypot.db'}",
        "AUTH_SECRET_KEY": "unit-test-secret-not-for-deployment",
        "AGENT_ID": "agent-unit-test",
        "AGENT_TOKEN": "token-unit-test",
        "ALLOWED_ORIGINS": "http://testserver,http://localhost:3001",
        "PHANTOMLAYER_URL": "http://phantomlayer.test",
    }
)

import pytest
from fastapi.testclient import TestClient

from app.auth import sessions
from app.config import HONEYPOT_CUSTOMER_ID, REAL_CUSTOMER_ID
from app.db import Database
from app.gateway import Decision, GatewayService
from app.main import app
from app.seed import seed_database


class StubDecisionClient:
    def __init__(self, target: str = "real"):
        self.target = target
        self.decisions: list[tuple[str, str]] = []
        self.observations: list[dict] = []

    def decide(self, *, session_id: str, operation: str, client_ip: str | None) -> Decision:
        self.decisions.append((session_id, operation))
        return Decision(
            decision_id="00000000-0000-4000-8000-000000000001",
            session_id=session_id,
            target="honeypot" if operation in {"list_tables", "enumerate_api", "get_customers", "enumerate_accounts", "enumerate_transactions", "probe_admin", "credential_probe"} else self.target,
            risk_score=72 if operation in {"list_tables", "enumerate_api", "get_customers"} else 8,
            attack_stage="reconnaissance" if operation in {"list_tables", "enumerate_api", "get_customers"} else "normal",
            triggered_rules=["RULE_RECONNAISSANCE"] if operation in {"list_tables", "enumerate_api", "get_customers"} else [],
        )

    def observe(self, *, decision: Decision, success: bool, exposed_entities: dict[str, int], response_count: int) -> None:
        self.observations.append({"decision": decision, "success": success, "exposed_entities": exposed_entities, "response_count": response_count})


@pytest.fixture
def databases(tmp_path):
    real = Database(f"sqlite:///{tmp_path / 'real.db'}", "real")
    honeypot = Database(f"sqlite:///{tmp_path / 'honeypot.db'}", "honeypot")
    real.init_schema()
    honeypot.init_schema()
    seed_database(real, "real")
    seed_database(honeypot, "honeypot")
    return real, honeypot


@pytest.fixture
def client(databases, monkeypatch):
    from app import main
    stub = StubDecisionClient()
    monkeypatch.setattr(main, "gateway", GatewayService({"real": databases[0], "honeypot": databases[1]}, stub))
    sessions.clear()
    with TestClient(app) as test_client:
        test_client.stub = stub
        yield test_client
    sessions.clear()
