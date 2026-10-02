from __future__ import annotations

import os
import pytest

from app.db import Database
from app.seed import seed_database


REAL_URL = os.environ.get("BANK_REAL_POSTGRES_TEST_URL")
HONEYPOT_URL = os.environ.get("BANK_HONEYPOT_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not REAL_URL or not HONEYPOT_URL,
    reason="set BANK_REAL_POSTGRES_TEST_URL and BANK_HONEYPOT_POSTGRES_TEST_URL for an explicit PostgreSQL smoke test",
)


def test_postgres_databases_seed_disjoint_markers():
    real = Database(REAL_URL, "real")
    honeypot = Database(HONEYPOT_URL, "honeypot")
    seed_database(real, "real")
    seed_database(honeypot, "honeypot")
    real_row = real.fetchone("SELECT full_name, customer_marker FROM bank_customers")
    honey_row = honeypot.fetchone("SELECT full_name, customer_marker FROM bank_customers")
    assert real_row == {"full_name": "Maya Bennett", "customer_marker": "REAL-MAYA-7Q4N"}
    assert honey_row == {"full_name": "John Carter", "customer_marker": "DECOY-JOHN-3M8Z"}
    assert real_row["customer_marker"] != honey_row["customer_marker"]

    # Exercise PostgreSQL's parameter binding, audit insert and transaction
    # paths, not just SQLite or seed queries.
    from app.gateway import GatewayService
    from app.auth import Session
    from app.config import REAL_CUSTOMER_ID
    from conftest import StubDecisionClient
    gateway = GatewayService({'real': real, 'honeypot': honeypot}, StubDecisionClient())
    result = gateway.login(email='maya.bennett@northstar.test', password='DemoMaya!2025', client_ip='127.0.0.1')
    assert result.success
    session = Session('00000000-0000-4000-8000-000000000077', REAL_CUSTOMER_ID,
                      'Maya Bennett','maya.bennett@northstar.test','real','csrf',0,9999999999)
    before = gateway.execute(session=session, operation='get_balance').data['total_balance_cents']
    transfer = {'source_account_id':'real-account-everyday-001','beneficiary_id':'real-beneficiary-alex-001',
                'amount_cents':1250,'reference':'PostgreSQL QA','idempotency_key':'pg-smoke'}
    first = gateway.execute(session=session, operation='create_transfer', payload=transfer)
    second = gateway.execute(session=session, operation='create_transfer', payload=transfer)
    assert first.data['id'] == second.data['id']
    assert gateway.execute(session=session, operation='get_balance').data['total_balance_cents'] == before - 1250
    from concurrent.futures import ThreadPoolExecutor
    concurrent_transfer = {**transfer, 'idempotency_key':'pg-concurrent', 'amount_cents':100}
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: gateway.execute(session=session, operation='create_transfer', payload=concurrent_transfer), range(6)))
    assert len({result.data['id'] for result in results}) == 1
    assert gateway.execute(session=session, operation='get_balance').data['total_balance_cents'] == before - 1350
    decoy = gateway.execute(session=session, operation='get_customers')
    assert decoy.data[0]['full_name'] == 'John Carter'
    assert real.fetchone("SELECT COUNT(*) AS count FROM gateway_audit WHERE operation = 'get_customers'")['count'] == 0
    assert honeypot.fetchone("SELECT COUNT(*) AS count FROM gateway_audit WHERE operation = 'get_customers'")['count'] == 1
