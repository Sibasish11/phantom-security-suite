from dataclasses import dataclass


@dataclass(frozen=True)
class RuleMatch:
    rule: str
    score: int
    reason: str


@dataclass(frozen=True)
class RoutingAssessment:
    risk_score: int
    severity: str
    suspicious: bool
    final_target: str
    rules: list[RuleMatch]
    reason: str


VALID_OPERATIONS = {
    "health_check",
    "list_tables",
    "get_users",
    "get_customers",
    "get_products",
    "get_orders",
    "get_customer",
    "get_order",
    "get_user",
}


SENSITIVE_OPERATIONS = {
    "get_users",
    "get_customers",
    "get_customer",
    "get_user",
}


RECONNAISSANCE_OPERATIONS = {
    "list_tables",
}


def _severity(score: int) -> str:
    if score == 0:
        return "LOW"

    if score <= 30:
        return "LOW"

    if score <= 50:
        return "MEDIUM"

    if score <= 75:
        return "HIGH"

    return "CRITICAL"


def assess_request(
    *,
    operation: str,
    session_history_count: int = 0,
    active_honeypot_session: bool = False,
) -> RoutingAssessment:
    rules: list[RuleMatch] = []

    if operation not in VALID_OPERATIONS:
        rules.append(
            RuleMatch(
                rule="RULE_INVALID_OPERATION",
                score=50,
                reason=f"Operation '{operation}' is not recognized",
            )
        )

    if operation in SENSITIVE_OPERATIONS:
        rules.append(
            RuleMatch(
                rule="RULE_SENSITIVE_DATA_ACCESS",
                score=60,
                reason=(
                    f"Operation '{operation}' accesses "
                    "sensitive user/customer data"
                ),
            )
        )

    if operation in RECONNAISSANCE_OPERATIONS:
        rules.append(
            RuleMatch(
                rule="RULE_ENUMERATION",
                score=30,
                reason="Request attempts to enumerate database structure",
            )
        )

        rules.append(
            RuleMatch(
                rule="RULE_RECONNAISSANCE",
                score=40,
                reason="Database reconnaissance request detected",
            )
        )

    if session_history_count >= 1 and (
        operation in SENSITIVE_OPERATIONS
        or operation in RECONNAISSANCE_OPERATIONS
    ):
        rules.append(
            RuleMatch(
                rule="RULE_REPEATED_ACCESS",
                score=35,
                reason="Repeated suspicious access detected in session",
            )
        )

    risk_score = min(
        100,
        sum(rule.score for rule in rules),
    )

    suspicious = risk_score > 0

    if active_honeypot_session:
        final_target = "honeypot"
        routing_reason = (
            "Active honeypot session pinned to HONEYPOT"
        )
    elif risk_score >= 50:
        final_target = "honeypot"
        routing_reason = (
            f"Risk score {risk_score} requires HONEYPOT routing"
        )
    else:
        final_target = "real"
        routing_reason = (
            f"Low-risk request preserved on REAL database "
            f"(score {risk_score})"
        )

    return RoutingAssessment(
        risk_score=risk_score,
        severity=_severity(risk_score),
        suspicious=suspicious,
        final_target=final_target,
        rules=rules,
        reason=routing_reason,
    )