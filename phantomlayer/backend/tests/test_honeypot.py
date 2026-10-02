import pytest
from fastapi.testclient import TestClient

from app.gateway.schemas import GatewayOperation, GatewayTarget
from app.honeypot.schemas import AttackStage
from app.honeypot.service import honeypot_session_manager
from app.main import app
from app.routing.schemas import RoutingRequest
from app.routing.service import automatic_routing_service
from app.security_logging.service import event_store


@pytest.fixture
def client(authenticated_client):
    return authenticated_client


@pytest.fixture(autouse=True)
def clear_sessions_and_events():
    honeypot_session_manager.clear()
    event_store.clear()
    yield
    honeypot_session_manager.clear()
    event_store.clear()


# 1. Session creation
def test_session_creation():
    session = honeypot_session_manager.get_or_create_session(
        client_ip="192.168.1.100",
        user_agent="Mozilla/5.0 Scanner",
    )
    assert session is not None
    assert session.session_id.startswith("sess_")
    assert session.client_ip == "192.168.1.100"
    assert session.user_agent == "Mozilla/5.0 Scanner"
    assert session.attack_stage == AttackStage.RECONNAISSANCE
    assert session.interaction_count == 0
    assert honeypot_session_manager.count() == 1


# 2. Automatic UUID/Session generation on honeypot routing
def test_automatic_session_generation(client):
    response = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customers",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["final_target"] == "honeypot"
    assert data["session_id"] is not None
    assert data["session_id"].startswith("sess_")
    assert data["attack_stage"] == "enumeration"
    assert data["interaction_count"] == 1
    assert honeypot_session_manager.count() == 1


# Normal request to REAL does not create session
def test_normal_request_does_not_create_session(client):
    response = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_products",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["final_target"] == "real"
    assert data["session_id"] is None
    assert data["attack_stage"] is None
    assert data["interaction_count"] is None
    assert honeypot_session_manager.count() == 0


# 3. Explicit session ID reuse
def test_explicit_session_id_reuse(client):
    session_id = "sess_attacker_custom_001"
    resp1 = client.post("/routing/route", json={
        "target": "real",
        "operation": "list_tables",
        "session_id": session_id,
    })
    assert resp1.status_code == 200
    assert resp1.json()["session_id"] == session_id
    assert resp1.json()["interaction_count"] == 1

    resp2 = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customers",
        "session_id": session_id,
    })
    assert resp2.status_code == 200
    assert resp2.json()["session_id"] == session_id
    assert resp2.json()["interaction_count"] == 2

    session = honeypot_session_manager.get_session(session_id)
    assert session is not None
    assert session.interaction_count == 2
    assert len(session.interactions) == 2


# 4. Session isolation
def test_session_isolation(client):
    sess_a = "sess_target_alpha"
    sess_b = "sess_target_bravo"

    client.post("/routing/route", json={
        "target": "real",
        "operation": "list_tables",
        "session_id": sess_a,
    })

    client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customers",
        "session_id": sess_b,
    })

    session_a = honeypot_session_manager.get_session(sess_a)
    session_b = honeypot_session_manager.get_session(sess_b)

    assert session_a.interaction_count == 1
    assert session_b.interaction_count == 1
    assert session_a.attack_stage == AttackStage.RECONNAISSANCE
    assert session_b.attack_stage == AttackStage.ENUMERATION
    assert len(session_a.exposed_entities.customer_ids) == 0
    assert len(session_b.exposed_entities.customer_ids) > 0


# 5. Interaction counting
@pytest.mark.asyncio
async def test_interaction_counting():
    session_id = "sess_counter_test"
    for step in range(1, 4):
        req = RoutingRequest(
            target="real",
            operation="get_customers",
            session_id=session_id,
        )
        resp = await automatic_routing_service.route(req)
        assert resp.interaction_count == step


# 6. Attack-stage progression
def test_attack_stage_progression(client):
    session_id = "sess_lifecycle_test"

    # Step 1: list_tables -> reconnaissance
    r1 = client.post("/routing/route", json={
        "target": "real",
        "operation": "list_tables",
        "session_id": session_id,
    })
    assert r1.json()["attack_stage"] == "reconnaissance"

    # Step 2: get_customers -> enumeration
    r2 = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customers",
        "session_id": session_id,
    })
    assert r2.json()["attack_stage"] == "enumeration"

    # Step 3: get_customer (single entity) -> exploration
    r3 = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customer",
        "parameters": {"id": 1},
        "session_id": session_id,
    })
    assert r3.json()["attack_stage"] == "exploration"

    # Step 4: repeated data access -> exfiltration
    r4 = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_orders",
        "session_id": session_id,
    })
    assert r4.json()["attack_stage"] == "exfiltration"

    # Step 5: get_user targeting internal user -> credential_access
    r5 = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_user",
        "parameters": {"username": "sysadmin"},
        "session_id": session_id,
    })
    assert r5.json()["attack_stage"] == "credential_access"


# 7. Entity tracking
def test_entity_tracking(client):
    session_id = "sess_entity_test"

    client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customers",
        "session_id": session_id,
    })

    session = honeypot_session_manager.get_session(session_id)
    assert session is not None
    assert 1 in session.exposed_entities.customer_ids
    assert "james.anderson@corp.example" in session.exposed_entities.customer_emails
    assert session.exposed_entities.has_customer(1)
    assert session.exposed_entities.has_customer("james.anderson@corp.example")


# 8. Customer drill-down
def test_customer_drilldown(client):
    # Lookup by ID
    resp1 = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customer",
        "parameters": {"id": 1},
    })
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["gateway_success"] is True
    assert len(data1["gateway_result"]) == 1
    assert data1["gateway_result"][0]["email"] == "james.anderson@corp.example"
    assert data1["gateway_result"][0]["first_name"] == "James"

    # Lookup by Email
    resp2 = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customer",
        "parameters": {"email": "linda.thomas@corp.example"},
    })
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["gateway_success"] is True
    assert len(data2["gateway_result"]) == 1
    assert data2["gateway_result"][0]["first_name"] == "Linda"


# 9. Customer -> orders consistency
def test_customer_to_orders_consistency(client):
    session_id = "sess_consistency_test"

    # Step 1: retrieve customer 1
    resp_cust = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customer",
        "parameters": {"id": 1},
        "session_id": session_id,
    })
    assert resp_cust.json()["gateway_result"][0]["first_name"] == "James"

    # Step 2: request orders for customer 1
    resp_orders = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_orders",
        "parameters": {"customer_id": 1},
        "session_id": session_id,
    })
    assert resp_orders.status_code == 200
    orders = resp_orders.json()["gateway_result"]

    # James Anderson (customer 1) has orders HPD-2024-0001 and HPD-2024-0008
    assert len(orders) == 2
    order_nums = {o["order_number"] for o in orders}
    assert order_nums == {"HPD-2024-0001", "HPD-2024-0008"}
    assert all(o["customer_id"] == 1 for o in orders)


# 10. Order -> order items / payment consistency
def test_order_to_items_and_payments_consistency(client):
    resp = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_order",
        "parameters": {"order_number": "HPD-2024-0001"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["gateway_success"] is True
    order = data["gateway_result"][0]
    assert order["order_number"] == "HPD-2024-0001"
    assert order["customer_id"] == 1

    # Check child order items with product details
    assert len(order["items"]) >= 1
    assert "product_name" in order["items"][0]
    assert "product_sku" in order["items"][0]
    assert order["items"][0]["product_name"] == "Honeypot Deception Appliance"

    # Check child payments
    assert len(order["payments"]) >= 1
    assert order["payments"][0]["transaction_id"] == "hp_txn_001"


# 11. Repeated sensitive access detection (RULE_REPEATED_ACCESS)
def test_repeated_sensitive_access_detection(client):
    session_id = "sess_repeated_access_test"

    # Request 1: first sensitive query
    r1 = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customers",
        "session_id": session_id,
    })
    rules1 = [r["rule"] for r in r1.json()["triggered_rules"]]
    assert "RULE_SENSITIVE_DATA_ACCESS" in rules1
    assert "RULE_REPEATED_ACCESS" not in rules1
    score1 = r1.json()["risk_score"]

    # Request 2: second sensitive query in the same session
    r2 = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customer",
        "parameters": {"id": 1},
        "session_id": session_id,
    })
    rules2 = [r["rule"] for r in r2.json()["triggered_rules"]]
    assert "RULE_SENSITIVE_DATA_ACCESS" in rules2
    assert "RULE_REPEATED_ACCESS" in rules2
    assert any("Repeated access" in reason for reason in r2.json()["reasons"])
    # Score must be elevated by repeated access rule
    assert r2.json()["risk_score"] > score1


# 12. Security event session correlation
def test_security_event_session_correlation(client):
    session_id = "sess_telemetry_corr_test"

    client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customers",
        "session_id": session_id,
    })

    # Retrieve events filtered by session_id
    response = client.get(f"/logging/events?session_id={session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3

    event_types = {e["event_type"] for e in data["events"]}
    assert "request_analyzed" in event_types
    assert "suspicious_request" in event_types
    assert "routing_decision" in event_types
    assert "honeypot_interaction" in event_types

    for event in data["events"]:
        assert event["session_id"] == session_id


# 13. Honeypot monitoring endpoints
def test_honeypot_monitoring_endpoints(client):
    # Health check
    health_resp = client.get("/honeypot/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["service"] == "PhantomLayer Interactive Honeypot"
    assert health_data["status"] == "healthy"
    assert "reconnaissance" in health_data["attack_stages_supported"]

    # Create activity
    session_id = "sess_admin_monitor_test"
    client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customers",
        "session_id": session_id,
    })

    # List sessions
    list_resp = client.get("/honeypot/sessions")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    session_ids = [s["session_id"] for s in list_data["sessions"]]
    assert session_id in session_ids

    # Detail session
    detail_resp = client.get(f"/honeypot/sessions/{session_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["session_id"] == session_id
    assert detail_data["attack_stage"] == "enumeration"
    assert len(detail_data["interactions"]) == 1
    assert detail_data["interactions"][0]["operation"] == "get_customers"


# 14. Session deletion
def test_session_deletion(client):
    session_id = "sess_delete_test"
    client.post("/routing/route", json={
        "target": "real",
        "operation": "list_tables",
        "session_id": session_id,
    })

    # Delete session
    del_resp = client.delete(f"/honeypot/sessions/{session_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["session_id"] == session_id

    # Verify not found
    get_resp = client.get(f"/honeypot/sessions/{session_id}")
    assert get_resp.status_code == 404


# 15. Production isolation: honeypot queries NEVER execute against REAL DB
def test_production_isolation(client):
    resp = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_customers",
    })
    data = resp.json()
    assert data["final_target"] == "honeypot"

    # All returned emails must be fake corporate domains, never real consumer demo emails
    emails = {c["email"] for c in data["gateway_result"]}
    assert all("corp.example" in e for e in emails)
    assert not any("email.com" in e for e in emails)
    assert not any("phantomlayer.demo" in e for e in emails)


# 16. Invalid operation preserves operation name (Step 10)
def test_invalid_operation_preserves_operation_name(client):
    session_id = "sess_invalid_op_test"
    resp = client.post("/routing/route", json={
        "target": "real",
        "operation": "drop_table",
        "session_id": session_id,
    })
    assert resp.status_code == 200
    data = resp.json()
    # Operation must NOT be renamed to health_check
    assert data["operation"] == "drop_table"
    assert data["gateway_success"] is False
    assert data["gateway_error"] == "Unsupported operation: drop_table"
    assert data["routing_decision"] == "routed_to_honeypot"
    assert data["session_id"] == session_id
