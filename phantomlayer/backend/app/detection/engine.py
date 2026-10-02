from app.detection.schemas import (
    DetectionRequest,
    DetectionResult,
    DetectionRule,
    RecommendedTarget,
    Severity,
    TriggeredRule,
)


class DetectionEngine:
    def __init__(self):
        # The original structured gateway operations remain supported. These
        # additional names are the stable operation contract for protected
        # customer APIs (currently the PhantomBank demo). The detector knows
        # the names, but it never receives or executes customer SQL.
        self._sensitive_operations = {
            "get_users",
            "get_customers",
            "get_customer",
            "get_user",
            "enumerate_customers",
            "enumerate_accounts",
            "enumerate_transactions",
            "probe_admin",
            "credential_probe",
        }
        self._reconnaissance_operations = {
            "list_tables",
            "enumerate_api",
        }
        self._valid_operations = {
            "health_check",
            "list_tables",
            "get_users",
            "get_customers",
            "get_products",
            "get_orders",
            "get_customer",
            "get_order",
            "get_user",
            "login",
            "get_accounts",
            "get_balance",
            "get_transactions",
            "get_beneficiaries",
            "get_cards",
            "create_transfer",
            "get_profile",
            "enumerate_api",
            "enumerate_customers",
            "enumerate_accounts",
            "enumerate_transactions",
            "probe_admin",
            "credential_probe",
        }

    def analyze(self, request: DetectionRequest) -> DetectionResult:
        triggered_rules = []
        reasons = []

        self._check_sensitive_data_access(request, triggered_rules, reasons)
        self._check_enumeration(request, triggered_rules, reasons)
        self._check_invalid_operation(request, triggered_rules, reasons)
        self._check_honeypot_target(request, triggered_rules, reasons)
        self._check_reconnaissance(request, triggered_rules, reasons)
        self._check_repeated_access(request, triggered_rules, reasons)


        risk_score = self._calculate_risk_score(triggered_rules)
        severity = self._calculate_severity(risk_score)
        suspicious = risk_score > 0
        recommended_target = self._determine_recommended_target(request, triggered_rules, risk_score)

        return DetectionResult(
            suspicious=suspicious,
            risk_score=risk_score,
            severity=severity,
            triggered_rules=triggered_rules,
            reasons=reasons,
            recommended_target=recommended_target,
        )

    def _check_sensitive_data_access(
        self,
        request: DetectionRequest,
        triggered_rules: list[TriggeredRule],
        reasons: list[str],
    ) -> None:
        if request.operation in self._sensitive_operations:
            triggered_rules.append(
                TriggeredRule(
                    rule=DetectionRule.RULE_SENSITIVE_DATA_ACCESS,
                    description="Request attempts to access sensitive user or customer data",
                    severity=Severity.HIGH,
                    score=60,
                )
            )
            reasons.append(f"Operation '{request.operation}' accesses sensitive data (users/customers)")

    def _check_enumeration(
        self,
        request: DetectionRequest,
        triggered_rules: list[TriggeredRule],
        reasons: list[str],
    ) -> None:
        if request.operation in self._reconnaissance_operations:
            triggered_rules.append(
                TriggeredRule(
                    rule=DetectionRule.RULE_ENUMERATION,
                    description="Request attempts to enumerate database structure",
                    severity=Severity.MEDIUM,
                    score=30,
                )
            )
            reasons.append(f"Operation '{request.operation}' performs database enumeration")

    def _check_invalid_operation(
        self,
        request: DetectionRequest,
        triggered_rules: list[TriggeredRule],
        reasons: list[str],
    ) -> None:
        if request.operation not in self._valid_operations:
            triggered_rules.append(
                TriggeredRule(
                    rule=DetectionRule.RULE_INVALID_OPERATION,
                    description="Request uses an unknown or invalid operation",
                    severity=Severity.HIGH,
                    score=50,
                )
            )
            reasons.append(f"Operation '{request.operation}' is not a recognized operation")

    def _check_honeypot_target(
        self,
        request: DetectionRequest,
        triggered_rules: list[TriggeredRule],
        reasons: list[str],
    ) -> None:
        if request.target == "honeypot":
            triggered_rules.append(
                TriggeredRule(
                    rule=DetectionRule.RULE_HONEYPOT_TARGET,
                    description="Request explicitly targets the honeypot database",
                    severity=Severity.CRITICAL,
                    score=80,
                )
            )
            reasons.append("Target is 'honeypot' - attacker may be probing deception infrastructure")

    def _check_reconnaissance(
        self,
        request: DetectionRequest,
        triggered_rules: list[TriggeredRule],
        reasons: list[str],
    ) -> None:
        if request.operation in self._reconnaissance_operations and request.target == "real":
            triggered_rules.append(
                TriggeredRule(
                    rule=DetectionRule.RULE_RECONNAISSANCE,
                    description="Reconnaissance operation targeting real database",
                    severity=Severity.HIGH,
                    score=40,
                )
            )
            reasons.append(f"Reconnaissance operation '{request.operation}' directed at real database")

    def _check_repeated_access(
        self,
        request: DetectionRequest,
        triggered_rules: list[TriggeredRule],
        reasons: list[str],
    ) -> None:
        if request.session_history_count and request.session_history_count >= 1:
            is_suspicious_or_sensitive = (
                request.operation in self._sensitive_operations
                or request.operation in self._reconnaissance_operations
                or request.target == "honeypot"
            )
            if is_suspicious_or_sensitive:
                triggered_rules.append(
                    TriggeredRule(
                        rule=DetectionRule.RULE_REPEATED_ACCESS,
                        description="Repeated suspicious or sensitive data access detected in session",
                        severity=Severity.MEDIUM,
                        score=35,
                    )
                )
                reasons.append(
                    f"Repeated access detected in session ({request.session_history_count} previous interactions)"
                )


    def _calculate_risk_score(self, triggered_rules: list[TriggeredRule]) -> int:
        if not triggered_rules:
            return 0
        total = sum(rule.score for rule in triggered_rules)
        return min(total, 100)

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

    def _determine_recommended_target(
        self,
        request: DetectionRequest,
        triggered_rules: list[TriggeredRule],
        risk_score: int,
    ) -> RecommendedTarget:
        if request.target == "honeypot":
            return RecommendedTarget.REAL
        if risk_score >= 50:
            return RecommendedTarget.HONEYPOT
        return RecommendedTarget.REAL


detection_engine = DetectionEngine()