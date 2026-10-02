from datetime import datetime, timezone
from threading import Lock
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import delete, func, select

from app.database import get_sync_control_db_manager
from app.honeypot.schemas import (
    AttackStage,
    AttackerSession,
    ExposedEntityTracker,
    HoneypotInteractionRecord,
)
from app.models.control_plane import (
    AttackSession,
    AttackSessionInteraction,
)


STAGE_RANKS = {
    AttackStage.RECONNAISSANCE: 0,
    AttackStage.ENUMERATION: 1,
    AttackStage.EXPLORATION: 2,
    AttackStage.EXFILTRATION: 3,
    AttackStage.CREDENTIAL_ACCESS: 4,
}


class HoneypotSessionManager:
    """
    Persistent attacker-session manager.

    PostgreSQL is the source of truth.
    The in-memory dictionary is only a fast cache for the current
    backend process.

    The manager intentionally does not store production database
    credentials or production data.
    """

    def __init__(self):
        self._sessions: dict[str, AttackerSession] = {}
        self._lock = Lock()

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_entities(
        entities: ExposedEntityTracker,
    ) -> dict[str, list[Any]]:
        return {
            "customer_ids": list(entities.customer_ids),
            "customer_emails": list(entities.customer_emails),
            "order_ids": list(entities.order_ids),
            "order_numbers": list(entities.order_numbers),
            "user_ids": list(entities.user_ids),
            "usernames": list(entities.usernames),
            "external_entity_counts": dict(entities.external_entity_counts),
        }

    @staticmethod
    def _deserialize_entities(
        value: Any,
    ) -> ExposedEntityTracker:
        if not isinstance(value, dict):
            return ExposedEntityTracker()

        return ExposedEntityTracker(
            customer_ids=[
                int(v)
                for v in value.get("customer_ids", [])
                if isinstance(v, int) or str(v).isdigit()
            ],
            customer_emails=[
                str(v)
                for v in value.get("customer_emails", [])
            ],
            order_ids=[
                int(v)
                for v in value.get("order_ids", [])
                if isinstance(v, int) or str(v).isdigit()
            ],
            order_numbers=[
                str(v)
                for v in value.get("order_numbers", [])
            ],
            user_ids=[
                int(v)
                for v in value.get("user_ids", [])
                if isinstance(v, int) or str(v).isdigit()
            ],
            usernames=[
                str(v)
                for v in value.get("usernames", [])
            ],
            external_entity_counts={
                str(key): int(count)
                for key, count in value.get("external_entity_counts", {}).items()
                if isinstance(key, str) and isinstance(count, int) and count >= 0
            },
        )

    @staticmethod
    def _serialize_json(value: Any) -> str:
        import json

        return json.dumps(
            value,
            default=str,
            separators=(",", ":"),
        )

    @staticmethod
    def _deserialize_json(value: Optional[str], default: Any) -> Any:
        import json

        if not value:
            return default

        try:
            return json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return default

    # ------------------------------------------------------------------
    # Database hydration
    # ------------------------------------------------------------------

    def _hydrate_session(
        self,
        record: AttackSession,
        interaction_records: list[AttackSessionInteraction],
    ) -> AttackerSession:
        entities = self._deserialize_entities(
            self._deserialize_json(
                record.exposed_entities_json,
                {},
            )
        )

        metadata = self._deserialize_json(
            record.metadata_json,
            {},
        )

        interactions: list[HoneypotInteractionRecord] = []

        for interaction in interaction_records:
            interaction_entities = self._deserialize_json(
                interaction.entities_exposed_json,
                {},
            )

            try:
                attack_stage = AttackStage(interaction.attack_stage)
            except ValueError:
                attack_stage = AttackStage.RECONNAISSANCE

            interactions.append(
                HoneypotInteractionRecord(
                    step=interaction.step,
                    timestamp=interaction.timestamp,
                    operation=interaction.operation,
                    parameters=self._deserialize_json(
                        interaction.parameters_json,
                        {},
                    ),
                    risk_score=interaction.risk_score,
                    attack_stage=attack_stage,
                    entities_exposed=interaction_entities,
                    success=interaction.success,
                    details=interaction.details,
                )
            )

        try:
            attack_stage = AttackStage(record.attack_stage)
        except ValueError:
            attack_stage = AttackStage.RECONNAISSANCE

        return AttackerSession(
            session_id=record.session_id,
            created_at=record.created_at,
            last_active_at=record.last_active_at,
            client_ip=record.client_ip,
            user_agent=record.user_agent,
            attack_stage=attack_stage,
            interaction_count=record.interaction_count,
            interactions=interactions,
            exposed_entities=entities,
            metadata=metadata,
        )

    def _load_session_from_db(
        self,
        session_id: str,
        organization_id: Any = None,
    ) -> Optional[AttackerSession]:
        db = get_sync_control_db_manager()

        with db.session() as session:
            query = select(AttackSession).where(
                AttackSession.session_id == session_id
            )
            if organization_id is not None:
                query = query.where(AttackSession.organization_id == organization_id)
            record = session.execute(query).scalar_one_or_none()

            if record is None:
                return None

            interaction_records = session.execute(
                select(AttackSessionInteraction)
                .where(
                    AttackSessionInteraction.session_id == record.id
                )
                .order_by(AttackSessionInteraction.step)
            ).scalars().all()

            return self._hydrate_session(
                record,
                interaction_records,
            )

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _trusted_ownership() -> tuple[Any, Any]:
        try:
            from app.security_context import current_context
            context = current_context()
        except (ImportError, LookupError, RuntimeError):
            context = None
        return (
            getattr(context, "organization_id", None),
            getattr(context, "domain_id", None),
        )

    def _create_db_session(
        self,
        session_model: AttackerSession,
    ) -> None:
        db = get_sync_control_db_manager()
        organization_id, domain_id = self._trusted_ownership()

        with db.session() as session:
            existing = session.execute(
                select(AttackSession).where(
                    AttackSession.session_id == session_model.session_id
                )
            ).scalar_one_or_none()

            if existing is not None:
                return

            record = AttackSession(
                session_id=session_model.session_id,
                organization_id=organization_id,
                domain_id=domain_id,
                client_ip=session_model.client_ip,
                user_agent=session_model.user_agent,
                attack_stage=session_model.attack_stage.value,
                interaction_count=session_model.interaction_count,
                exposed_entities_json=self._serialize_json(
                    self._serialize_entities(
                        session_model.exposed_entities
                    )
                ),
                metadata_json=self._serialize_json(
                    session_model.metadata
                ),
                created_at=session_model.created_at,
                last_active_at=session_model.last_active_at,
            )

            session.add(record)
            session.commit()

    def _persist_session(
        self,
        session_model: AttackerSession,
    ) -> None:
        db = get_sync_control_db_manager()
        organization_id, domain_id = self._trusted_ownership()

        with db.session() as session:
            record = session.execute(
                select(AttackSession).where(
                    AttackSession.session_id == session_model.session_id
                )
            ).scalar_one_or_none()

            if record is None:
                record = AttackSession(
                    session_id=session_model.session_id,
                    created_at=session_model.created_at,
                )
                session.add(record)

            if record.organization_id is None and organization_id is not None:
                record.organization_id = organization_id
            if record.domain_id is None and domain_id is not None:
                record.domain_id = domain_id
            record.client_ip = session_model.client_ip
            record.user_agent = session_model.user_agent
            record.attack_stage = session_model.attack_stage.value
            record.interaction_count = session_model.interaction_count
            record.exposed_entities_json = self._serialize_json(
                self._serialize_entities(
                    session_model.exposed_entities
                )
            )
            record.metadata_json = self._serialize_json(
                session_model.metadata
            )
            record.created_at = session_model.created_at
            record.last_active_at = session_model.last_active_at

            session.commit()

    def _persist_interaction(
        self,
        session_model: AttackerSession,
        interaction: HoneypotInteractionRecord,
    ) -> None:
        db = get_sync_control_db_manager()
        organization_id, domain_id = self._trusted_ownership()

        with db.session() as session:
            attack_session = session.execute(
                select(AttackSession).where(
                    AttackSession.session_id == session_model.session_id
                )
            ).scalar_one_or_none()

            if attack_session is None:
                attack_session = AttackSession(
                    session_id=session_model.session_id,
                    organization_id=organization_id,
                    domain_id=domain_id,
                    client_ip=session_model.client_ip,
                    user_agent=session_model.user_agent,
                    attack_stage=session_model.attack_stage.value,
                    interaction_count=session_model.interaction_count,
                    exposed_entities_json=self._serialize_json(
                        self._serialize_entities(
                            session_model.exposed_entities
                        )
                    ),
                    metadata_json=self._serialize_json(
                        session_model.metadata
                    ),
                    created_at=session_model.created_at,
                    last_active_at=session_model.last_active_at,
                )
                session.add(attack_session)
                session.flush()

            interaction_record = AttackSessionInteraction(
                session_id=attack_session.id,
                step=interaction.step,
                operation=interaction.operation,
                parameters_json=self._serialize_json(
                    interaction.parameters
                ),
                risk_score=interaction.risk_score,
                attack_stage=interaction.attack_stage.value,
                entities_exposed_json=self._serialize_json(
                    interaction.entities_exposed
                ),
                success=interaction.success,
                details=interaction.details,
                timestamp=interaction.timestamp,
            )

            session.add(interaction_record)

            if attack_session.organization_id is None and organization_id is not None:
                attack_session.organization_id = organization_id
            if attack_session.domain_id is None and domain_id is not None:
                attack_session.domain_id = domain_id
            attack_session.client_ip = session_model.client_ip
            attack_session.user_agent = session_model.user_agent
            attack_session.attack_stage = session_model.attack_stage.value
            attack_session.interaction_count = session_model.interaction_count
            attack_session.exposed_entities_json = self._serialize_json(
                self._serialize_entities(
                    session_model.exposed_entities
                )
            )
            attack_session.metadata_json = self._serialize_json(
                session_model.metadata
            )
            attack_session.last_active_at = session_model.last_active_at

            session.commit()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def generate_session_id(self) -> str:
        return f"sess_{uuid4().hex[:16]}"

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AttackerSession:
        with self._lock:
            # Fast path: memory cache.
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]

                session.last_active_at = datetime.now(timezone.utc)

                if client_ip and not session.client_ip:
                    session.client_ip = client_ip

                if user_agent and not session.user_agent:
                    session.user_agent = user_agent

                self._persist_session(session)

                return session

            # Persistent path: recover a session after restart.
            if session_id:
                existing = self._load_session_from_db(session_id)

                if existing is not None:
                    existing.last_active_at = datetime.now(timezone.utc)

                    if client_ip and not existing.client_ip:
                        existing.client_ip = client_ip

                    if user_agent and not existing.user_agent:
                        existing.user_agent = user_agent

                    self._sessions[session_id] = existing
                    self._persist_session(existing)

                    return existing

            # New session.
            new_id = session_id or self.generate_session_id()
            now = datetime.now(timezone.utc)

            session = AttackerSession(
                session_id=new_id,
                created_at=now,
                last_active_at=now,
                client_ip=client_ip,
                user_agent=user_agent,
                attack_stage=AttackStage.RECONNAISSANCE,
                interaction_count=0,
                interactions=[],
                exposed_entities=ExposedEntityTracker(),
                metadata={},
            )

            self._sessions[new_id] = session
            self._create_db_session(session)

            return session

    def get_session(
        self,
        session_id: str,
        organization_id: Any = None,
    ) -> Optional[AttackerSession]:
        with self._lock:
            # The control database is authoritative across workers/restarts.
            # An in-process cache must not hide externally ingested activity.
            session = self._load_session_from_db(session_id, organization_id=organization_id)

            if session is not None:
                self._sessions[session_id] = session

            return session

    def list_sessions(self, organization_id: Any = None) -> list[AttackerSession]:
        with self._lock:
            db = get_sync_control_db_manager()

            with db.session() as session:
                query = select(AttackSession)
                if organization_id is not None:
                    query = query.where(AttackSession.organization_id == organization_id)
                records = session.execute(
                    query.order_by(AttackSession.last_active_at.desc())
                ).scalars().all()

                hydrated: list[AttackerSession] = []

                for record in records:
                    interaction_records = session.execute(
                        select(AttackSessionInteraction)
                        .where(
                            AttackSessionInteraction.session_id == record.id
                        )
                        .order_by(
                            AttackSessionInteraction.step
                        )
                    ).scalars().all()

                    attacker_session = self._hydrate_session(
                        record,
                        interaction_records,
                    )

                    self._sessions[record.session_id] = attacker_session
                    hydrated.append(attacker_session)

                return hydrated

    def delete_session(
        self,
        session_id: str,
        organization_id: Any = None,
    ) -> bool:
        with self._lock:
            db = get_sync_control_db_manager()

            with db.session() as session:
                query = select(AttackSession).where(
                    AttackSession.session_id == session_id
                )
                if organization_id is not None:
                    query = query.where(AttackSession.organization_id == organization_id)
                record = session.execute(query).scalar_one_or_none()

                if record is None:
                    self._sessions.pop(session_id, None)
                    return False

                session.delete(record)
                session.commit()

            self._sessions.pop(session_id, None)
            return True

    def clear(self) -> None:
        """
        Test/development helper.

        Clears all persisted attacker sessions and the local cache.
        """
        with self._lock:
            db = get_sync_control_db_manager()

            with db.session() as session:
                session.execute(
                    delete(AttackSessionInteraction)
                )
                session.execute(
                    delete(AttackSession)
                )
                session.commit()

            self._sessions.clear()

    def count(self, organization_id: Any = None) -> int:
        db = get_sync_control_db_manager()

        with db.session() as session:
            query = select(func.count(AttackSession.id))
            if organization_id is not None:
                query = query.where(AttackSession.organization_id == organization_id)
            return int(session.execute(query).scalar_one())

    # ------------------------------------------------------------------
    # Interaction tracking
    # ------------------------------------------------------------------

    def record_interaction(
        self,
        session_id: str,
        operation: str,
        parameters: Optional[dict[str, Any]] = None,
        risk_score: int = 0,
        data: Any = None,
        success: bool = True,
        details: Optional[str] = None,
        external_entity_counts: Optional[dict[str, int]] = None,
    ) -> HoneypotInteractionRecord:
        with self._lock:
            session = self._sessions.get(session_id)

            if session is None:
                session = self._load_session_from_db(session_id)

            if session is None:
                now = datetime.now(timezone.utc)

                session = AttackerSession(
                    session_id=session_id,
                    created_at=now,
                    last_active_at=now,
                    attack_stage=AttackStage.RECONNAISSANCE,
                    interaction_count=0,
                    interactions=[],
                    exposed_entities=ExposedEntityTracker(),
                    metadata={},
                )

                self._create_db_session(session)

            self._sessions[session_id] = session

            session.last_active_at = datetime.now(timezone.utc)
            session.interaction_count += 1

            parameters = parameters or {}

            entities_exposed: dict[str, list[Any]] = {
                "customers": [],
                "orders": [],
                "users": [],
            }

            self._extract_and_track_entities(
                session,
                operation,
                data,
                entities_exposed,
            )

            # External integrations send counts only. Never turn those counts
            # into records or persist customer identifiers in this service.
            if external_entity_counts:
                safe_counts = {
                    str(key): int(value)
                    for key, value in external_entity_counts.items()
                    if isinstance(key, str)
                    and isinstance(value, int)
                    and 0 <= value <= 100000
                }
                session.exposed_entities.add_external_counts(safe_counts)
                for entity_type, count in safe_counts.items():
                    entities_exposed[entity_type] = count

            new_stage = self._classify_attack_stage(
                session,
                operation,
                parameters,
            )

            if (
                STAGE_RANKS.get(new_stage, 0)
                >= STAGE_RANKS.get(session.attack_stage, 0)
            ):
                session.attack_stage = new_stage

            record = HoneypotInteractionRecord(
                step=session.interaction_count,
                timestamp=datetime.now(timezone.utc),
                operation=operation,
                parameters={key: value for key, value in parameters.items()
                            if key in {'limit', 'offset', 'id', 'customer_id', 'order_id', 'user_id'}
                            and isinstance(value, int) and not isinstance(value, bool)
                            and 0 <= value <= 1000000},
                risk_score=risk_score,
                attack_stage=session.attack_stage,
                entities_exposed=entities_exposed,
                success=success,
                details=details,
            )

            session.interactions.append(record)

            self._persist_interaction(
                session,
                record,
            )

            return record

    # ------------------------------------------------------------------
    # Entity tracking
    # ------------------------------------------------------------------

    def _extract_and_track_entities(
        self,
        session: AttackerSession,
        operation: str,
        data: Any,
        entities_exposed: dict[str, list[Any]],
    ) -> None:
        if not data:
            return

        rows = data if isinstance(data, list) else [data]

        for row in rows:
            if not isinstance(row, dict):
                continue

            # Customer entities.
            if (
                "email" in row
                and (
                    "first_name" in row
                    or "last_name" in row
                    or "city" in row
                )
            ):
                cid = row.get("id")
                email = row.get("email")

                session.exposed_entities.add_customer(
                    customer_id=cid,
                    email=email,
                )

                if cid:
                    entities_exposed["customers"].append(
                        {
                            "id": cid,
                            "email": email,
                        }
                    )

            # Order entities.
            if "order_number" in row:
                oid = row.get("id")
                order_number = row.get("order_number")

                session.exposed_entities.add_order(
                    order_id=oid,
                    order_number=order_number,
                )

                if order_number:
                    entities_exposed["orders"].append(
                        {
                            "id": oid,
                            "order_number": order_number,
                        }
                    )

            # User entities.
            if "username" in row:
                uid = row.get("id")
                username = row.get("username")

                session.exposed_entities.add_user(
                    user_id=uid,
                    username=username,
                )

                if username:
                    entities_exposed["users"].append(
                        {
                            "id": uid,
                            "username": username,
                        }
                    )

    # ------------------------------------------------------------------
    # Attack-stage state machine
    # ------------------------------------------------------------------

    def _classify_attack_stage(
        self,
        session: AttackerSession,
        current_op: str,
        parameters: dict[str, Any],
    ) -> AttackStage:
        # Credential access.
        if current_op in (
            "get_user",
            "get_credentials",
        ):
            return AttackStage.CREDENTIAL_ACCESS

        if current_op == "get_users" and (
            parameters.get("username") == "sysadmin"
            or parameters.get("role") == "admin"
        ):
            return AttackStage.CREDENTIAL_ACCESS

        sensitive_ops = {
            "get_users",
            "get_customers",
            "get_orders",
            "get_customer",
            "get_order",
            "get_user",
        }

        previous_sensitive_count = sum(
            1
            for interaction in session.interactions
            if interaction.operation in sensitive_ops
        )

        # Repeated harvesting.
        if (
            current_op
            in (
                "get_customers",
                "get_orders",
                "get_customer",
                "get_order",
            )
            and previous_sensitive_count >= 2
        ):
            return AttackStage.EXFILTRATION

        # Single-record drill-down.
        if current_op in (
            "get_customer",
            "get_order",
        ):
            return AttackStage.EXPLORATION

        # Bulk enumeration.
        if current_op in (
            "get_customers",
            "get_users",
            "get_products",
            "get_orders",
        ):
            return AttackStage.ENUMERATION

        # Initial reconnaissance.
        if current_op in (
            "list_tables",
            "health_check",
        ):
            return AttackStage.RECONNAISSANCE

        return session.attack_stage


honeypot_session_manager = HoneypotSessionManager()