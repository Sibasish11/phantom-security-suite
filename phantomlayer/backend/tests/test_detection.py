import pytest
from fastapi.testclient import TestClient

from app.detection.engine import detection_engine
from app.detection.schemas import (
    DetectionRequest,
    DetectionRule,
    RecommendedTarget,
    Severity,
)
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_detection_engine_initializes():
    assert detection_engine is not None


def test_normal_low_risk_request():
    request = DetectionRequest(target="real", operation="health_check")
    result = detection_engine.analyze(request)

    assert result.suspicious is False
    assert result.risk_score == 0
    assert result.severity == Severity.LOW
    assert len(result.triggered_rules) == 0
    assert len(result.reasons) == 0
    assert result.recommended_target == RecommendedTarget.REAL


def test_sensitive_data_request_get_users():
    request = DetectionRequest(target="real", operation="get_users")
    result = detection_engine.analyze(request)

    assert result.suspicious is True
    assert result.risk_score >= 60
    assert result.severity in [Severity.HIGH, Severity.CRITICAL]
    assert any(r.rule == DetectionRule.RULE_SENSITIVE_DATA_ACCESS for r in result.triggered_rules)
    assert any("get_users" in reason for reason in result.reasons)
    assert result.recommended_target == RecommendedTarget.HONEYPOT


def test_sensitive_data_request_get_customers():
    request = DetectionRequest(target="real", operation="get_customers")
    result = detection_engine.analyze(request)

    assert result.suspicious is True
    assert result.risk_score >= 60
    assert any(r.rule == DetectionRule.RULE_SENSITIVE_DATA_ACCESS for r in result.triggered_rules)
    assert result.recommended_target == RecommendedTarget.HONEYPOT


def test_reconnaissance_table_enumeration():
    request = DetectionRequest(target="real", operation="list_tables")
    result = detection_engine.analyze(request)

    assert result.suspicious is True
    assert any(r.rule == DetectionRule.RULE_ENUMERATION for r in result.triggered_rules)
    assert any(r.rule == DetectionRule.RULE_RECONNAISSANCE for r in result.triggered_rules)
    assert result.risk_score >= 70
    assert result.severity in [Severity.HIGH, Severity.CRITICAL]
    assert result.recommended_target == RecommendedTarget.HONEYPOT


def test_invalid_operation():
    request = DetectionRequest(target="real", operation="drop_table")
    result = detection_engine.analyze(request)

    assert result.suspicious is True
    assert any(r.rule == DetectionRule.RULE_INVALID_OPERATION for r in result.triggered_rules)
    assert any("drop_table" in reason for reason in result.reasons)
    assert result.risk_score >= 50
    assert result.recommended_target == RecommendedTarget.HONEYPOT


def test_explicit_honeypot_target():
    request = DetectionRequest(target="honeypot", operation="health_check")
    result = detection_engine.analyze(request)

    assert result.suspicious is True
    assert any(r.rule == DetectionRule.RULE_HONEYPOT_TARGET for r in result.triggered_rules)
    assert any("honeypot" in reason.lower() for reason in result.reasons)
    assert result.risk_score >= 80
    assert result.severity == Severity.CRITICAL
    assert result.recommended_target == RecommendedTarget.REAL


def test_multiple_triggered_rules():
    request = DetectionRequest(target="real", operation="list_tables")
    result = detection_engine.analyze(request)

    rule_names = [r.rule for r in result.triggered_rules]
    assert DetectionRule.RULE_ENUMERATION in rule_names
    assert DetectionRule.RULE_RECONNAISSANCE in rule_names
    assert len(result.triggered_rules) >= 2


def test_risk_score_boundaries():
    request = DetectionRequest(target="real", operation="get_products")
    result = detection_engine.analyze(request)

    assert result.risk_score == 0
    assert result.severity == Severity.LOW

    request = DetectionRequest(target="honeypot", operation="health_check")
    result = detection_engine.analyze(request)
    assert result.risk_score <= 100

    request = DetectionRequest(target="real", operation="list_tables")
    result = detection_engine.analyze(request)
    assert result.risk_score <= 100


def test_severity_calculation():
    request = DetectionRequest(target="real", operation="health_check")
    result = detection_engine.analyze(request)
    assert result.severity == Severity.LOW

    request = DetectionRequest(target="real", operation="list_tables")
    result = detection_engine.analyze(request)
    assert result.severity in [Severity.HIGH, Severity.CRITICAL]

    request = DetectionRequest(target="honeypot", operation="health_check")
    result = detection_engine.analyze(request)
    assert result.severity == Severity.CRITICAL


def test_recommended_target_logic():
    request = DetectionRequest(target="real", operation="get_users")
    result = detection_engine.analyze(request)
    assert result.recommended_target == RecommendedTarget.HONEYPOT

    request = DetectionRequest(target="real", operation="health_check")
    result = detection_engine.analyze(request)
    assert result.recommended_target == RecommendedTarget.REAL

    request = DetectionRequest(target="honeypot", operation="health_check")
    result = detection_engine.analyze(request)
    assert result.recommended_target == RecommendedTarget.REAL


def test_detection_health_endpoint(client):
    response = client.get("/detection/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "PhantomLayer Detection Engine"
    assert data["status"] == "healthy"
    assert "rules_loaded" in data
    assert "RULE_SENSITIVE_DATA_ACCESS" in data["rules_loaded"]
    assert "RULE_ENUMERATION" in data["rules_loaded"]


def test_detection_analyze_endpoint_normal(client):
    response = client.post("/detection/analyze", json={
        "target": "real",
        "operation": "health_check",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["suspicious"] is False
    assert data["risk_score"] == 0
    assert data["severity"] == "LOW"
    assert data["recommended_target"] == "real"


def test_detection_analyze_endpoint_sensitive_data(client):
    response = client.post("/detection/analyze", json={
        "target": "real",
        "operation": "get_users",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["suspicious"] is True
    assert data["risk_score"] >= 60
    assert data["severity"] in ["HIGH", "CRITICAL"]
    assert data["recommended_target"] == "honeypot"
    assert any(r["rule"] == "RULE_SENSITIVE_DATA_ACCESS" for r in data["triggered_rules"])


def test_detection_analyze_endpoint_reconnaissance(client):
    response = client.post("/detection/analyze", json={
        "target": "real",
        "operation": "list_tables",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["suspicious"] is True
    rule_names = {r["rule"] for r in data["triggered_rules"]}
    assert "RULE_ENUMERATION" in rule_names
    assert "RULE_RECONNAISSANCE" in rule_names


def test_detection_analyze_endpoint_invalid_operation(client):
    response = client.post("/detection/analyze", json={
        "target": "real",
        "operation": "invalid_op",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["suspicious"] is True
    assert any(r["rule"] == "RULE_INVALID_OPERATION" for r in data["triggered_rules"])


def test_detection_analyze_endpoint_honeypot_target(client):
    response = client.post("/detection/analyze", json={
        "target": "honeypot",
        "operation": "health_check",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["suspicious"] is True
    assert data["risk_score"] >= 80
    assert data["severity"] == "CRITICAL"
    assert data["recommended_target"] == "real"
    assert any(r["rule"] == "RULE_HONEYPOT_TARGET" for r in data["triggered_rules"])


def test_detection_analyze_multiple_rules(client):
    response = client.post("/detection/analyze", json={
        "target": "real",
        "operation": "list_tables",
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["triggered_rules"]) >= 2
    rule_names = {r["rule"] for r in data["triggered_rules"]}
    assert "RULE_ENUMERATION" in rule_names
    assert "RULE_RECONNAISSANCE" in rule_names


def test_detection_analyze_get_orders_low_risk(client):
    response = client.post("/detection/analyze", json={
        "target": "real",
        "operation": "get_orders",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["suspicious"] is False
    assert data["risk_score"] == 0
    assert data["recommended_target"] == "real"


def test_detection_analyze_get_products_low_risk(client):
    response = client.post("/detection/analyze", json={
        "target": "real",
        "operation": "get_products",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["suspicious"] is False
    assert data["risk_score"] == 0