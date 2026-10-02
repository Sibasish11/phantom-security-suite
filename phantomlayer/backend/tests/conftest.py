"""Safety gate for tests whose historic fixtures mutate persistent stores."""

import os

import pytest
from sqlalchemy import make_url


def pytest_sessionstart(session):
    # Refuse destructive legacy integration fixtures outside the dedicated QA
    # runner. Pure detector/schema/unit tests can still run without PostgreSQL.
    requested = session.config.args
    safe_modules = {
        "tests/test_detection.py", "tests/test_risk.py",
    }
    unit_only = requested and all(str(arg).split("::")[0] in safe_modules for arg in requested)
    if unit_only:
        return
    if os.environ.get("PHANTOMLAYER_TEST_DATABASES") != "1":
        raise pytest.UsageError("Database tests must run via scripts/test-backend.sh")
    for key in ("REAL_DATABASE_URL", "HONEYPOT_DATABASE_URL", "CONTROL_DATABASE_URL"):
        if not (make_url(os.environ.get(key, "")).database or "").startswith("phantomlayer_qa_"):
            raise pytest.UsageError("Refusing tests against a non-QA database")


@pytest.fixture
def trusted_test_context():
    """Real persisted tenant identity for legacy gateway/service tests."""
    from uuid import uuid4
    from app.database import get_sync_control_db_manager
    from app.models.control_plane import Organization, OrganizationUser, Domain, OrganizationRole
    from app.auth.tokens import create_access_token
    from app.security_context import TrustedContext, use_context
    with get_sync_control_db_manager().session() as db:
        org = Organization(name=f"QA {uuid4()}", slug=f"qa-{uuid4()}")
        db.add(org)
        db.flush()
        user = OrganizationUser(organization_id=org.id, email=f"{uuid4()}@example.test",
            full_name="QA Analyst", password_hash="not-used-for-login", role=OrganizationRole.ADMIN)
        domain = Domain(organization_id=org.id, domain=f"{uuid4()}.example.test",
            verification_record_name="_phantomlayer.example.test", verification_token="qa", verified=True)
        db.add_all([user, domain])
        db.flush()
        token = create_access_token(user.id, org.id, "admin")
        context = TrustedContext(organization_id=org.id, domain_id=domain.id)
        db.commit()
    with use_context(context):
        yield {"Authorization": f"Bearer {token}", "X-Domain-ID": str(domain.id)}


@pytest.fixture
def authenticated_client(trusted_test_context):
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app, headers=trusted_test_context)


@pytest.fixture
def memory_event_store(monkeypatch):
    """Exercise legacy logger unit contracts using its supported memory adapter.

    New persistence tests separately exercise PostgreSQL and fresh-store reads.
    No auth dependency is overridden and no production code is test-gated.
    """
    from app.security_logging.service import event_store
    monkeypatch.setattr(event_store, "_persistent", False)
    event_store.clear()
    yield event_store
    event_store.clear()
