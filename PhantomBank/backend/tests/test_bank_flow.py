from __future__ import annotations

from app.auth import Session
import pytest
from app.gateway import GatewayService, ProtectionUnavailable, SensitiveOperationDenied
from app.config import HONEYPOT_CUSTOMER_ID
from conftest import StubDecisionClient


def signed_headers(client, *, csrf: bool = True):
    headers = {"Origin": "http://testserver"}
    if csrf:
        headers["X-CSRF-Token"] = client.cookies.get("bank_csrf")
    return headers


def login(client):
    response = client.post(
        "/api/auth/login",
        headers={"Origin": "http://testserver"},
        json={"email": "maya.bennett@northstar.test", "password": "DemoMaya!2025"},
    )
    assert response.status_code == 200
    return response


def test_health_and_login_return_customer_shape_without_routing_fields(client):
    assert client.get("/health").json() == {"status": "healthy", "service": "PhantomBank"}
    response = login(client)
    body = response.json()
    assert body["user"] == {"full_name": "Maya Bennett", "email": "maya.bennett@northstar.test"}
    assert "target" not in body and "risk_score" not in body


def test_account_flow_uses_server_session_and_real_seed(client):
    login(client)
    response = client.get("/api/accounts")
    assert response.status_code == 200
    accounts = response.json()["accounts"]
    assert {item["account_type"] for item in accounts} == {"Everyday", "Savings"}
    assert all("Maya" not in item for item in accounts)
    assert "target" not in response.text and "risk_score" not in response.text


def test_transfer_is_transactional_and_idempotent(client):
    login(client)
    accounts = client.get("/api/accounts").json()["accounts"]
    beneficiaries = client.get("/api/beneficiaries").json()["beneficiaries"]
    before = client.get("/api/balance").json()["total_balance_cents"]
    headers = {**signed_headers(client), "X-Idempotency-Key": "test-transfer-001"}
    payload = {"source_account_id": accounts[0]["id"], "beneficiary_id": beneficiaries[0]["id"], "amount": "12.50", "reference": "Test transfer"}
    first = client.post("/api/transfers", headers=headers, json=payload)
    second = client.post("/api/transfers", headers=headers, json=payload)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["transfer"]["id"] == second.json()["transfer"]["id"]
    assert second.json()["transfer"]["idempotent_replay"] is True
    after = client.get("/api/balance").json()["total_balance_cents"]
    assert before - after == 1250


def test_origin_and_csrf_protect_writes(client):
    response = client.post("/api/auth/login", json={"email": "maya.bennett@northstar.test", "password": "DemoMaya!2025"})
    assert response.status_code == 403
    login(client)
    response = client.post("/api/auth/logout", headers={"Origin": "http://testserver"})
    assert response.status_code == 403


def test_sensitive_operation_is_deception_only_and_is_not_publicly_labeled(client):
    login(client)
    response = client.get("/api/security/list-tables")
    assert response.status_code == 200
    assert "gateway_audit" in response.json()["result"]
    assert "honeypot" not in response.text
    assert "risk_score" not in response.text


def test_gateway_fails_closed_before_database_when_decision_unavailable(databases):
    class Unavailable:
        def decide(self, **_):
            raise ProtectionUnavailable()
        def observe(self, **_):
            raise AssertionError("observe cannot run without a decision")

    service = GatewayService({"real": databases[0], "honeypot": databases[1]}, Unavailable())
    session = Session("00000000-0000-4000-8000-000000000010", "real-customer-maya-001", "Maya Bennett", "maya.bennett@northstar.test", "real", "csrf", 0, 9999999999)
    try:
        service.execute(session=session, operation="get_accounts")
    except ProtectionUnavailable:
        pass
    else:
        raise AssertionError("decision outage must fail closed")


def test_honeypot_session_can_never_be_promoted_to_real_data(databases):
    class RealOnly(StubDecisionClient):
        def decide(self, *, session_id, operation, client_ip):
            decision = super().decide(session_id=session_id, operation=operation, client_ip=client_ip)
            return decision.__class__(decision.decision_id, decision.session_id, "real", decision.risk_score, decision.attack_stage, decision.triggered_rules)

    service = GatewayService({"real": databases[0], "honeypot": databases[1]}, RealOnly())
    session = Session("00000000-0000-4000-8000-000000000012", "decoy-customer-john-991", "John Carter", "john.carter@vaultline.test", "honeypot", "csrf", 0, 9999999999)
    try:
        service.execute(session=session, operation="get_accounts")
    except SensitiveOperationDenied:
        pass
    else:
        raise AssertionError("a deception session must not reach the real dataset")


def test_honeypot_destination_contains_disjoint_synthetic_customer(databases):
    stub = StubDecisionClient(target="honeypot")
    service = GatewayService({"real": databases[0], "honeypot": databases[1]}, stub)
    session = Session("00000000-0000-4000-8000-000000000011", "real-customer-maya-001", "Maya Bennett", "maya.bennett@northstar.test", "real", "csrf", 0, 9999999999)
    result = service.execute(session=session, operation="get_customers")
    assert result.data[0]["id"] == HONEYPOT_CUSTOMER_ID
    assert result.data[0]["full_name"] == "John Carter"
    assert stub.observations[-1]["exposed_entities"]["customers"] == 1


def test_bootstrap_preserves_existing_ledger(databases):
    from app.seed import seed_database
    real, _ = databases
    with real.transaction() as cursor:
        cursor.execute("UPDATE accounts SET balance_cents = balance_cents - 10 WHERE id = 'real-account-everyday-001'")
    before = real.query('SELECT * FROM accounts ORDER BY id')
    seed_database(real, 'real')
    assert real.query('SELECT * FROM accounts ORDER BY id') == before


def test_auth_rejects_invalid_password_missing_or_tampered_cookie(client):
    assert client.get('/api/accounts').status_code == 401
    assert client.post('/api/auth/login', headers={'Origin': 'http://testserver'},
        json={'email':'maya.bennett@northstar.test','password':'wrong'}).status_code == 401
    login(client)
    cookie = client.cookies.get('bank_session')
    client.cookies.clear()
    client.cookies.set('bank_session', cookie + 'invalid')
    assert client.get('/api/accounts').status_code == 401


def test_expired_bank_session_is_401(client, monkeypatch):
    import time
    login(client)
    future = time.time() + 7200
    monkeypatch.setattr('app.auth.time.time', lambda: future)
    assert client.get('/api/accounts').status_code == 401


@pytest.mark.parametrize('amount', ['0', '-1', '1.001', '1000000.01'])
def test_invalid_transfer_amount_does_not_change_balances(client, amount):
    login(client)
    before = client.get('/api/balance').json()
    response = client.post('/api/transfers', headers={**signed_headers(client), 'X-Idempotency-Key':'invalid-amount'},
        json={'amount':amount,'source_account_id':'real-account-everyday-001','beneficiary_id':'real-beneficiary-alex-001'})
    assert response.status_code == 422
    assert client.get('/api/balance').json() == before


def test_transfer_denies_other_account_and_conflicting_replay(client):
    login(client)
    payload = {'amount':'10.00','source_account_id':'decoy-account-ops-991','beneficiary_id':'real-beneficiary-alex-001'}
    headers = {**signed_headers(client), 'X-Idempotency-Key':'conflict-test'}
    before = client.get('/api/balance').json()
    assert client.post('/api/transfers', headers=headers, json=payload).status_code == 409
    assert client.get('/api/balance').json() == before
    payload['source_account_id'] = 'real-account-everyday-001'
    assert client.post('/api/transfers', headers=headers, json=payload).status_code == 200
    payload['amount'] = '11.00'
    assert client.post('/api/transfers', headers=headers, json=payload).status_code == 409
