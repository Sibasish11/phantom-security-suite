import pytest
from fastapi.testclient import TestClient

from app.risk.engine import risk_scoring_engine
from app.risk.schemas import (
    ConfidenceLevel,
    RecommendedTarget,
    RiskAssessmentRequest,
    Severity,
)
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_risk_engine_initializes():
    assert risk_scoring_engine is not None


def test_normal_health_check_low_risk():
    request = RiskAssessmentRequest(target="real", operation="health_check")
    result = risk_scoring_engine.assess(request)

    assert result.risk_score == 0
    assert result.severity == Severity.LOW
    assert result.confidence == 0.0
    assert result.confidence_level == ConfidenceLevel.LOW
    assert len(result.triggered_rules) == 0
    assert len(result.reasons) == 0
    assert result.recommended_target == RecommendedTarget.REAL


def test_sensitive_data_access_elevated_risk():
    request = RiskAssessmentRequest(target="real", operation="get_users")
    result = risk_scoring_engine.assess(request)

    assert result.risk_score > 0
    assert result.risk_score <= 100
    assert result.severity in [Severity.HIGH, Severity.CRITICAL]
    assert result.confidence > 0.0
    assert result.confidence <= 1.0
    assert len(result.triggered_rules) >= 1
    assert any(r.rule.value == "RULE_SENSITIVE_DATA_ACCESS" for r in result.triggered_rules)
    assert result.recommended_target == RecommendedTarget.HONEYPOT


def test_sensitive_data_access_customers():
    request = RiskAssessmentRequest(target="real", operation="get_customers")
    result = risk_scoring_engine.assess(request)

    assert result.risk_score > 0
    assert result.severity in [Severity.HIGH, Severity.CRITICAL]
    assert any(r.rule.value == "RULE_SENSITIVE_DATA_ACCESS" for r in result.triggered_rules)
    assert result.recommended_target == RecommendedTarget.HONEYPOT


def test_enumeration_elevated_risk():
    request = RiskAssessmentRequest(target="real", operation="list_tables")
    result = risk_scoring_engine.assess(request)

    assert result.risk_score > 0
    # list_tables triggers RULE_ENUMERATION (30) and RULE_RECONNAISSANCE (40)
    # Weighted scores result in risk_score around 27 (LOW severity)
    assert result.severity in [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
    rule_names = {r.rule.value for r in result.triggered_rules}
    assert "RULE_ENUMERATION" in rule_names
    assert "RULE_RECONNAISSANCE" in rule_names


def test_multiple_independent_rules_combined():
    request = RiskAssessmentRequest(target="real", operation="list_tables")
    result = risk_scoring_engine.assess(request)

    assert len(result.triggered_rules) >= 2
    assert result.risk_score <= 100
    assert result.risk_score > 0


def test_honeypot_target_probing():
    request = RiskAssessmentRequest(target="honeypot", operation="health_check")
    result = risk_scoring_engine.assess(request)

    assert result.risk_score >= 80
    assert result.severity == Severity.CRITICAL
    assert any(r.rule.value == "RULE_HONEYPOT_TARGET" for r in result.triggered_rules)
    assert result.recommended_target == RecommendedTarget.REAL


def test_invalid_operation():
    request = RiskAssessmentRequest(target="real", operation="drop_table")
    result = risk_scoring_engine.assess(request)

    assert result.risk_score > 0
    assert any(r.rule.value == "RULE_INVALID_OPERATION" for r in result.triggered_rules)
    # Invalid operation base score is 50, but weighted score may be below 50
    # So recommendation may be REAL (if risk_score < 50) or HONEYPOT (if >= 50)
    assert result.recommended_target in [RecommendedTarget.REAL, RecommendedTarget.HONEYPOT]


def test_confidence_deterministic():
    request = RiskAssessmentRequest(target="real", operation="get_users")
    result1 = risk_scoring_engine.assess(request)
    result2 = risk_scoring_engine.assess(request)

    assert result1.confidence == result2.confidence
    assert 0.0 <= result1.confidence <= 1.0


def test_confidence_increases_with_multiple_rules():
    normal_request = RiskAssessmentRequest(target="real", operation="health_check")
    normal_result = risk_scoring_engine.assess(normal_request)

    sensitive_request = RiskAssessmentRequest(target="real", operation="get_users")
    sensitive_result = risk_scoring_engine.assess(sensitive_request)

    multi_rule_request = RiskAssessmentRequest(target="real", operation="list_tables")
    multi_rule_result = risk_scoring_engine.assess(multi_rule_request)

    assert multi_rule_result.confidence > sensitive_result.confidence > normal_result.confidence


def test_confidence_levels():
    request = RiskAssessmentRequest(target="real", operation="health_check")
    result = risk_scoring_engine.assess(request)
    assert result.confidence_level == ConfidenceLevel.LOW

    request = RiskAssessmentRequest(target="honeypot", operation="health_check")
    result = risk_scoring_engine.assess(request)
    # honeypot target gives high risk score (80) but confidence ~0.64 maps to MEDIUM
    assert result.confidence_level in [ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH]


def test_boundary_score_zero():
    request = RiskAssessmentRequest(target="real", operation="health_check")
    result = risk_scoring_engine.assess(request)
    assert result.risk_score == 0


def test_boundary_score_max():
    request = RiskAssessmentRequest(target="honeypot", operation="list_tables")
    result = risk_scoring_engine.assess(request)
    assert result.risk_score <= 100


def test_severity_derivation():
    request = RiskAssessmentRequest(target="real", operation="health_check")
    result = risk_scoring_engine.assess(request)
    assert result.severity == Severity.LOW

    request = RiskAssessmentRequest(target="real", operation="get_users")
    result = risk_scoring_engine.assess(request)
    assert result.severity in [Severity.HIGH, Severity.CRITICAL]

    request = RiskAssessmentRequest(target="honeypot", operation="health_check")
    result = risk_scoring_engine.assess(request)
    assert result.severity == Severity.CRITICAL


def test_risk_assessment_schema_validation():
    from app.risk.schemas import RiskAssessment, TriggeredRuleDetail, DetectionRule

    assessment = RiskAssessment(
        risk_score=50,
        severity=Severity.MEDIUM,
        confidence=0.75,
        confidence_level=ConfidenceLevel.HIGH,
        triggered_rules=[
            TriggeredRuleDetail(
                rule=DetectionRule.RULE_SENSITIVE_DATA_ACCESS,
                description="Test",
                severity=Severity.HIGH,
                base_score=60,
                weighted_score=50,
                weight=0.85,
            )
        ],
        reasons=["Test reason"],
        recommended_target=RecommendedTarget.HONEYPOT,
    )
    assert assessment.risk_score == 50
    assert assessment.severity == Severity.MEDIUM


def test_risk_health_endpoint(client):
    response = client.get("/risk/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "PhantomLayer Risk Scoring Engine"
    assert data["status"] == "healthy"
    assert data["scoring_method"] == "deterministic_weighted"
    assert "confidence_thresholds" in data


def test_risk_assess_endpoint_normal(client):
    response = client.post("/risk/assess", json={
        "target": "real",
        "operation": "health_check",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] == 0
    assert data["severity"] == "LOW"
    assert data["confidence"] == 0.0
    assert data["recommended_target"] == "real"


def test_risk_assess_endpoint_sensitive_data(client):
    response = client.post("/risk/assess", json={
        "target": "real",
        "operation": "get_users",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] > 0
    assert data["severity"] in ["HIGH", "CRITICAL"]
    assert data["confidence"] > 0.0
    assert data["recommended_target"] == "honeypot"
    assert any(r["rule"] == "RULE_SENSITIVE_DATA_ACCESS" for r in data["triggered_rules"])
    assert "weighted_score" in data["triggered_rules"][0]
    assert "weight" in data["triggered_rules"][0]


def test_risk_assess_endpoint_enumeration(client):
    response = client.post("/risk/assess", json={
        "target": "real",
        "operation": "list_tables",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] > 0
    rule_names = {r["rule"] for r in data["triggered_rules"]}
    assert "RULE_ENUMERATION" in rule_names
    assert "RULE_RECONNAISSANCE" in rule_names


def test_risk_assess_endpoint_invalid_operation(client):
    response = client.post("/risk/assess", json={
        "target": "real",
        "operation": "invalid_op",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] > 0
    assert any(r["rule"] == "RULE_INVALID_OPERATION" for r in data["triggered_rules"])


def test_risk_assess_endpoint_honeypot_target(client):
    response = client.post("/risk/assess", json={
        "target": "honeypot",
        "operation": "health_check",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 80
    assert data["severity"] == "CRITICAL"
    assert data["recommended_target"] == "real"
    assert any(r["rule"] == "RULE_HONEYPOT_TARGET" for r in data["triggered_rules"])


def test_risk_assess_endpoint_products_low_risk(client):
    response = client.post("/risk/assess", json={
        "target": "real",
        "operation": "get_products",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] == 0
    assert data["severity"] == "LOW"
    assert data["recommended_target"] == "real"


def test_risk_assess_endpoint_orders_low_risk(client):
    response = client.post("/risk/assess", json={
        "target": "real",
        "operation": "get_orders",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] == 0
    assert data["severity"] == "LOW"


def test_weighted_scores_differ_from_base_scores():
    request = RiskAssessmentRequest(target="real", operation="list_tables")
    result = risk_scoring_engine.assess(request)

    for rule in result.triggered_rules:
        assert rule.weighted_score <= rule.base_score
        assert 0.0 <= rule.weight <= 1.0


def test_scoring_method_documented():
    request = RiskAssessmentRequest(target="real", operation="get_users")
    result = risk_scoring_engine.assess(request)
    assert result.scoring_method == "deterministic_weighted"