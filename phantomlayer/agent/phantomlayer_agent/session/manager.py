import secrets

from .models import AttackSession, SessionInteraction


class AttackSessionManager:
    def __init__(self):
        self._sessions: dict[str, AttackSession] = {}

    def create_session(self) -> AttackSession:
        session_id = (
            f"agent-{secrets.token_urlsafe(16)}"
        )

        session = AttackSession(
            session_id=session_id,
        )

        self._sessions[session_id] = session

        return session

    def get_session(
        self,
        session_id: str | None,
    ) -> AttackSession | None:
        if not session_id:
            return None

        return self._sessions.get(session_id)

    def get_or_create(
        self,
        session_id: str | None,
    ) -> AttackSession:
        existing = self.get_session(session_id)

        if existing is not None:
            return existing

        return self.create_session()

    def record_interaction(
        self,
        *,
        session_id: str,
        operation: str,
        target: str,
        risk_score: int,
        suspicious: bool,
    ) -> SessionInteraction:
        session = self.get_session(session_id)

        if session is None:
            raise ValueError(
                f"Unknown attack session: {session_id}"
            )

        attack_stage = self._determine_attack_stage(
            operation=operation,
            interaction_count=session.interaction_count,
        )

        return session.record(
            operation=operation,
            target=target,
            risk_score=risk_score,
            suspicious=suspicious,
            attack_stage=attack_stage,
        )

    def _determine_attack_stage(
        self,
        *,
        operation: str,
        interaction_count: int,
    ) -> str:
        if operation == "list_tables":
            return "reconnaissance"

        if operation in {
            "get_users",
            "get_customers",
            "get_customer",
            "get_user",
        }:
            return "credential_discovery"

        if operation in {
            "get_orders",
            "get_order",
            "get_products",
        }:
            if interaction_count >= 1:
                return "data_discovery"

            return "discovery"

        if operation == "health_check":
            return "probing"

        return "suspicious_activity"

    def list_sessions(self) -> list[AttackSession]:
        return list(self._sessions.values())

    def clear(self) -> None:
        self._sessions.clear()


attack_session_manager = AttackSessionManager()