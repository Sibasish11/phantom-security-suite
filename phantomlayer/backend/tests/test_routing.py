import pytest
from fastapi.testclient import TestClient

from app.routing.service import automatic_routing_service
from app.routing.schemas import (
    GatewayOperation,
    GatewayTarget,
    RecommendedTarget,
    RoutingDecision,
    RoutingRequest,
    Severity,
)
from app.main import app


@pytest.fixture
def client(authenticated_client):
    return authenticated_client


def test_routing_service_initializes():
    assert automatic_routing_service is not None


def test_routing_health_endpoint(client):
    response = client.get("/routing/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "PhantomLayer Automatic Routing"
    assert data["status"] in ["healthy", "degraded"]
    assert data["routing_policy"] == "risk_based_automatic"
    assert "detection_rules_active" in data
    assert "risk_scoring_active" in data


@pytest.mark.asyncio
async def test_low_risk_request_routes_to_real():
    request = RoutingRequest(target="real", operation="health_check")
    result = await automatic_routing_service.route(request)

    assert result.original_target == GatewayTarget.REAL
    assert result.final_target == GatewayTarget.REAL
    assert result.operation == GatewayOperation.HEALTH_CHECK
    assert result.risk_score == 0
    assert result.severity == Severity.LOW
    assert result.suspicious is False
    assert result.routing_decision == RoutingDecision.ORIGINAL_TARGET_PRESERVED
    assert "Low risk" in result.routing_reason
    assert result.gateway_success is True
    assert result.gateway_result is not None
    assert result.gateway_result[0]["health"] == 1


@pytest.mark.asyncio
async def test_sensitive_get_users_routes_to_honeypot():
    request = RoutingRequest(target="real", operation="get_users")
    result = await automatic_routing_service.route(request)

    assert result.original_target == GatewayTarget.REAL
    assert result.final_target == GatewayTarget.HONEYPOT
    assert result.operation == GatewayOperation.GET_USERS
    assert result.risk_score > 0
    assert result.severity in [Severity.HIGH, Severity.CRITICAL]
    assert result.suspicious is True
    assert result.routing_decision == RoutingDecision.ROUTED_TO_HONEYPOT
    assert "HONEYPOT" in result.routing_reason or "honeypot" in result.routing_reason.lower()
    assert result.gateway_success is True
    assert result.gateway_result is not None
    assert len(result.gateway_result) == 5
    assert result.gateway_result[0]["username"] == "sysadmin"


@pytest.mark.asyncio
async def test_get_customers_routes_to_honeypot():
    request = RoutingRequest(target="real", operation="get_customers")
    result = await automatic_routing_service.route(request)

    assert result.original_target == GatewayTarget.REAL
    assert result.final_target == GatewayTarget.HONEYPOT
    assert result.operation == GatewayOperation.GET_CUSTOMERS
    assert result.risk_score > 0
    assert result.severity in [Severity.HIGH, Severity.CRITICAL]
    assert result.routing_decision == RoutingDecision.ROUTED_TO_HONEYPOT
    assert result.gateway_success is True
    assert len(result.gateway_result) == 7


@pytest.mark.asyncio
async def test_reconnaissance_list_tables_routes_to_honeypot():
    request = RoutingRequest(target="real", operation="list_tables")
    result = await automatic_routing_service.route(request)

    assert result.original_target == GatewayTarget.REAL
    assert result.final_target == GatewayTarget.HONEYPOT
    assert result.operation == GatewayOperation.LIST_TABLES
    assert result.risk_score > 0
    assert result.suspicious is True
    assert result.routing_decision == RoutingDecision.ROUTED_TO_HONEYPOT
    rule_names = {r["rule"] for r in result.triggered_rules}
    assert "RULE_ENUMERATION" in rule_names
    assert "RULE_RECONNAISSANCE" in rule_names


@pytest.mark.asyncio
async def test_routing_response_contains_risk_information():
    request = RoutingRequest(target="real", operation="get_users")
    result = await automatic_routing_service.route(request)

    assert result.risk_score > 0
    assert result.severity is not None
    assert result.confidence > 0.0
    assert result.confidence_level is not None
    assert len(result.reasons) > 0
    assert len(result.triggered_rules) > 0


@pytest.mark.asyncio
async def test_triggered_rules_preserved():
    request = RoutingRequest(target="real", operation="list_tables")
    result = await automatic_routing_service.route(request)

    assert len(result.triggered_rules) >= 2
    for rule in result.triggered_rules:
        assert "rule" in rule
        assert "description" in rule
        assert "severity" in rule
        assert "base_score" in rule
        assert "weighted_score" in rule
        assert "weight" in rule


@pytest.mark.asyncio
async def test_routing_reason_populated():
    request = RoutingRequest(target="real", operation="get_users")
    result = await automatic_routing_service.route(request)

    assert result.routing_reason is not None
    assert len(result.routing_reason) > 0


@pytest.mark.asyncio
async def test_explicit_honeypot_target():
    request = RoutingRequest(target="honeypot", operation="health_check")
    result = await automatic_routing_service.route(request)

    assert result.original_target == GatewayTarget.HONEYPOT
    assert result.final_target == GatewayTarget.HONEYPOT
    assert result.operation == GatewayOperation.HEALTH_CHECK
    assert result.risk_score >= 80
    assert result.severity == Severity.CRITICAL
    assert result.routing_decision == RoutingDecision.ROUTED_TO_HONEYPOT
    assert result.gateway_success is True
    assert result.gateway_result[0]["health"] == 1


@pytest.mark.asyncio
async def test_no_recursive_routing():
    request = RoutingRequest(target="honeypot", operation="get_users")
    result = await automatic_routing_service.route(request)

    assert result.original_target == GatewayTarget.HONEYPOT
    assert result.final_target == GatewayTarget.HONEYPOT
    assert result.routing_decision == RoutingDecision.ROUTED_TO_HONEYPOT


@pytest.mark.asyncio
async def test_gateway_execution_uses_final_selected_target():
    request = RoutingRequest(target="real", operation="get_users")
    result = await automatic_routing_service.route(request)

    assert result.final_target == GatewayTarget.HONEYPOT
    assert result.gateway_result is not None
    assert len(result.gateway_result) == 5
    emails = {u["email"] for u in result.gateway_result}
    assert all("deception.local" in e for e in emails)


@pytest.mark.asyncio
async def test_real_and_honeypot_results_distinct():
    real_request = RoutingRequest(target="real", operation="health_check")
    hp_request = RoutingRequest(target="honeypot", operation="health_check")

    real_result = await automatic_routing_service.route(real_request)
    hp_result = await automatic_routing_service.route(hp_request)

    assert real_result.final_target == GatewayTarget.REAL
    assert hp_result.final_target == GatewayTarget.HONEYPOT


@pytest.mark.asyncio
async def test_invalid_operation_handled_safely():
    request = RoutingRequest(target="real", operation="drop_table")
    result = await automatic_routing_service.route(request)

    assert result.routing_decision == RoutingDecision.ROUTED_TO_HONEYPOT
    assert result.gateway_success is False
    assert result.gateway_error is not None


@pytest.mark.asyncio
async def test_invalid_target_rejected():
    request = RoutingRequest(target="invalid", operation="health_check")
    with pytest.raises(ValueError):
        await automatic_routing_service.route(request)


def test_routing_endpoint_normal(client):
    response = client.post("/routing/route", json={
        "target": "real",
        "operation": "health_check",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["original_target"] == "real"
    assert data["final_target"] == "real"
    assert data["operation"] == "health_check"
    assert data["risk_score"] == 0
    assert data["severity"] == "LOW"
    assert data["routing_decision"] == "original_target_preserved"
    assert data["gateway_success"] is True


def test_routing_endpoint_sensitive_data(client):
    response = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_users",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["original_target"] == "real"
    assert data["final_target"] == "honeypot"
    assert data["operation"] == "get_users"
    assert data["risk_score"] > 0
    assert data["severity"] in ["HIGH", "CRITICAL"]
    assert data["routing_decision"] == "routed_to_honeypot"
    assert data["gateway_success"] is True
    assert len(data["gateway_result"]) == 5


def test_routing_endpoint_reconnaissance(client):
    response = client.post("/routing/route", json={
        "target": "real",
        "operation": "list_tables",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["original_target"] == "real"
    assert data["final_target"] == "honeypot"
    assert data["risk_score"] > 0
    rule_names = {r["rule"] for r in data["triggered_rules"]}
    assert "RULE_ENUMERATION" in rule_names
    assert "RULE_RECONNAISSANCE" in rule_names


def test_routing_endpoint_honeypot_target(client):
    response = client.post("/routing/route", json={
        "target": "honeypot",
        "operation": "health_check",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["original_target"] == "honeypot"
    assert data["final_target"] == "honeypot"
    assert data["risk_score"] >= 80
    assert data["severity"] == "CRITICAL"
    assert data["routing_decision"] == "routed_to_honeypot"


def test_routing_endpoint_invalid_operation(client):
    response = client.post("/routing/route", json={
        "target": "real",
        "operation": "drop_table",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["routing_decision"] == "routed_to_honeypot"
    assert data["gateway_success"] is False
    assert data["gateway_error"] is not None


def test_routing_endpoint_invalid_target(client):
    response = client.post("/routing/route", json={
        "target": "invalid",
        "operation": "health_check",
    })
    assert response.status_code == 400


def test_routing_products_low_risk(client):
    response = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_products",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["final_target"] == "real"
    assert data["risk_score"] == 0
    assert data["routing_decision"] == "original_target_preserved"


def test_routing_orders_low_risk(client):
    response = client.post("/routing/route", json={
        "target": "real",
        "operation": "get_orders",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["final_target"] == "real"
    assert data["risk_score"] == 0