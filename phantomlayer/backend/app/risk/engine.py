from app.detection.engine import detection_engine
from app.detection.schemas import DetectionRequest, DetectionRule, Severity
from app.risk.schemas import (
    ConfidenceLevel,
    RecommendedTarget,
    RiskAssessment,
    RiskAssessmentRequest,
    TriggeredRuleDetail,
)


class RiskScoringEngine:
    def __init__(self):
        self._rule_weights = {
            DetectionRule.RULE_HONEYPOT_TARGET: 1.0,
            DetectionRule.RULE_SENSITIVE_DATA_ACCESS: 0.9,
            DetectionRule.RULE_RECONNAISSANCE: 0.85,
            DetectionRule.RULE_INVALID_OPERATION: 0.8,
            DetectionRule.RULE_ENUMERATION: 0.7,
            DetectionRule.RULE_REPEATED_ACCESS: 0.75,
        }

        self._severity_weights = {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.85,
            Severity.MEDIUM: 0.6,
            Severity.LOW: 0.3,
        }

    def assess(self, request: RiskAssessmentRequest) -> RiskAssessment:
        detection_request = DetectionRequest(
            target=request.target,
            operation=request.operation,
            parameters=request.parameters,
            client_ip=request.client_ip,
            user_agent=request.user_agent,
            session_id=request.session_id,
            session_history_count=request.session_history_count,
        )

        detection_result = detection_engine.analyze(detection_request)


        if not detection_result.triggered_rules:
            return RiskAssessment(
                risk_score=0,
                severity=Severity.LOW,
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                triggered_rules=[],
                reasons=[],
                recommended_target=RecommendedTarget.REAL,
            )

        triggered_details = []
        weighted_sum = 0.0
        total_weight = 0.0
        max_severity = Severity.LOW

        for rule in detection_result.triggered_rules:
            weight = self._rule_weights.get(rule.rule, 0.5)
            severity_weight = self._severity_weights.get(rule.severity, 0.5)

            combined_weight = (weight + severity_weight) / 2.0
            weighted_score = int(rule.score * combined_weight)

            weighted_sum += weighted_score * combined_weight
            total_weight += combined_weight

            if self._severity_rank(rule.severity) > self._severity_rank(max_severity):
                max_severity = rule.severity

            triggered_details.append(
                TriggeredRuleDetail(
                    rule=rule.rule,
                    description=rule.description,
                    severity=rule.severity,
                    base_score=rule.score,
                    weighted_score=weighted_score,
                    weight=combined_weight,
                )
            )

        base_score = int(weighted_sum / total_weight) if total_weight > 0 else 0
        has_repeated = any(r.rule == DetectionRule.RULE_REPEATED_ACCESS for r in triggered_details)
        if has_repeated:
            max_single = max((r.weighted_score for r in triggered_details), default=0)
            risk_score = min(100, max(base_score, max_single) + 15)
        else:
            risk_score = min(base_score, 100)


        severity = self._calculate_severity(risk_score)
        confidence = self._calculate_confidence(triggered_details, detection_result)
        confidence_level = self._confidence_to_level(confidence)
        recommended_target = self._determine_recommended_target(request, risk_score, detection_result)

        return RiskAssessment(
            risk_score=risk_score,
            severity=severity,
            confidence=confidence,
            confidence_level=confidence_level,
            triggered_rules=triggered_details,
            reasons=detection_result.reasons,
            recommended_target=recommended_target,
        )

    def _severity_rank(self, severity: Severity) -> int:
        return {
            Severity.LOW: 0,
            Severity.MEDIUM: 1,
            Severity.HIGH: 2,
            Severity.CRITICAL: 3,
        }.get(severity, 0)

    def _calculate_severity(self, risk_score: int) -> Severity:
        if risk_score == 0:
            return Severity.LOW
        elif risk_score <= 30:
            return Severity.LOW
        elif risk_score <= 50:
            return Severity.MEDIUM
        elif risk_score <= 75:
            return Severity.HIGH
        else:
            return Severity.CRITICAL

    def _calculate_confidence(self, triggered_details: list[TriggeredRuleDetail], detection_result) -> float:
        if not triggered_details:
            return 0.0

        num_rules = len(triggered_details)
        max_severity_rank = max(self._severity_rank(r.severity) for r in triggered_details)
        total_weight = sum(r.weight for r in triggered_details)
        avg_weight = total_weight / num_rules if num_rules > 0 else 0.0

        confidence = (0.25 * min(num_rules / 5.0, 1.0) +
                     0.35 * (max_severity_rank / 3.0) +
                     0.20 * avg_weight +
                     0.20 * min(len(detection_result.reasons) / 5.0, 1.0))

        return min(confidence, 1.0)

    def _confidence_to_level(self, confidence: float) -> ConfidenceLevel:
        if confidence >= 0.85:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.65:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.4:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _determine_recommended_target(self, request: RiskAssessmentRequest, risk_score: int, detection_result) -> RecommendedTarget:
        if request.target == "honeypot":
            return RecommendedTarget.REAL
        if risk_score >= 50:
            return RecommendedTarget.HONEYPOT
        return RecommendedTarget.REAL


risk_scoring_engine = RiskScoringEngine()