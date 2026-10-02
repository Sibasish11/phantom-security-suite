from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import logging
from collections import deque
from typing import Any, Protocol
from uuid import UUID, uuid4

import httpx

from .auth import Session, verify_password
from .config import HONEYPOT_CUSTOMER_ID, REAL_CUSTOMER_ID, settings
from .db import Database

logger = logging.getLogger(__name__)


OPERATIONS = {
    "login",
    "get_accounts",
    "get_balance",
    "get_transactions",
    "get_beneficiaries",
    "get_cards",
    "create_transfer",
    "get_profile",
    "list_tables",
    "enumerate_api",
    "get_customers",
    "enumerate_accounts",
    "enumerate_transactions",
    "probe_admin",
    "credential_probe",
}
SENSITIVE_OPERATIONS = {
    "list_tables",
    "enumerate_api",
    "get_customers",
    "enumerate_accounts",
    "enumerate_transactions",
    "probe_admin",
    "credential_probe",
}


class GatewayError(Exception):
    status_code = 502
    public_message = "The banking service is temporarily unavailable."


class ProtectionUnavailable(GatewayError):
    status_code = 503
    public_message = "Banking protection is temporarily unavailable. Please try again."


class SensitiveOperationDenied(GatewayError):
    status_code = 403
    public_message = "That request is not available."


class GatewayConflict(GatewayError):
    status_code = 409
    public_message = "This transfer request conflicts with an earlier request."


class GatewayDatabaseError(GatewayError):
    status_code = 502
    public_message = "The banking service could not complete that request."


@dataclass(frozen=True)
class Decision:
    decision_id: str
    session_id: str
    target: str
    risk_score: int
    attack_stage: str
    triggered_rules: list[str]
    # The bank keeps sending this opaque server-issued UUID on subsequent
    # decisions. `session_id` is PhantomLayer's internal namespaced handle.
    request_session_id: str = ""


@dataclass(frozen=True)
class GatewayResult:
    success: bool
    data: Any
    response_count: int
    target: str
    decision: Decision


class DecisionAdapter(Protocol):
    def decide(self, *, session_id: str, operation: str, client_ip: str | None) -> Decision: ...
    def observe(self, *, decision: Decision, success: bool, exposed_entities: dict[str, int], response_count: int) -> None: ...


class PhantomLayerDecisionClient:
    """The only route from this bank process to PhantomLayer's decision contract."""

    def __init__(self) -> None:
        self.base_url = settings.phantomlayer_url.rstrip("/")
        self.headers = {
            "X-Agent-ID": settings.agent_id,
            "X-Agent-Token": settings.agent_token,
        }

    def _ensure_configured(self) -> None:
        if not self.base_url or not self.headers["X-Agent-ID"] or not self.headers["X-Agent-Token"]:
            raise ProtectionUnavailable()

    def decide(self, *, session_id: str, operation: str, client_ip: str | None) -> Decision:
        self._ensure_configured()
        try:
            UUID(session_id)
            with httpx.Client(timeout=settings.phantomlayer_timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/integrations/bank/decision",
                    headers=self.headers,
                    json={
                        "session_id": session_id,
                        "operation": operation,
                        "client_ip": client_ip,
                    },
                )
                response.raise_for_status()
                body = response.json()
            decision_id = str(UUID(str(body["decision_id"])))
            returned_session = str(body["session_id"])
            if not returned_session or len(returned_session) > 160:
                raise ValueError("unexpected decision session")
            target = body["target"]
            if target not in {"real", "honeypot"}:
                raise ValueError("unexpected decision target")
            return Decision(
                decision_id=decision_id,
                session_id=returned_session,
                target=target,
                risk_score=int(body["risk_score"]),
                attack_stage=str(body["attack_stage"]),
                triggered_rules=[str(rule) for rule in body.get("triggered_rules", [])],
                request_session_id=session_id,
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            logger.warning("PhantomLayer decision unavailable: %s", exc)
            raise ProtectionUnavailable() from exc

    def observe(self, *, decision: Decision, success: bool, exposed_entities: dict[str, int], response_count: int) -> None:
        self._ensure_configured()
        try:
            with httpx.Client(timeout=settings.phantomlayer_timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/integrations/bank/observe",
                    headers=self.headers,
                    json={
                        "decision_id": decision.decision_id,
                        "success": success,
                        "exposed_entities": exposed_entities,
                        "response_count": response_count,
                    },
                )
                response.raise_for_status()
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            # The DB operation has already committed. Do not lie to the customer about it;
            # retain local evidence and make the observe failure visible in server logs.
            logger.error("PhantomLayer observe failed for %s: %s", decision.decision_id, exc)


class GatewayService:
    def __init__(self, databases: dict[str, Database], decision_client: DecisionAdapter | None = None):
        self.databases = databases
        self.decision_client = decision_client or PhantomLayerDecisionClient()
        self._evidence: deque[dict[str, Any]] = deque(maxlen=200)

    def _database(self, target: str) -> Database:
        return self.databases["honeypot" if target == "honeypot" else "real"]

    @staticmethod
    def _customer_id(target: str) -> str:
        return HONEYPOT_CUSTOMER_ID if target == "honeypot" else REAL_CUSTOMER_ID

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _row(row) -> dict | None:
        return dict(row) if row else None

    def _audit(self, cursor, database: Database, *, session_id: str, decision: Decision, operation: str, success: bool, response_count: int, entity_type: str | None, entity_count: int) -> None:
        cursor.execute(
            database.adapt("""
            INSERT INTO gateway_audit
            (id, session_id, decision_id, operation, destination, success, response_count, entity_type, entity_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """),
            (
                str(uuid4()), session_id, decision.decision_id, operation, decision.target,
                int(success), response_count, entity_type, entity_count, self._now(),
            ),
        )

    def _observe(self, *, decision: Decision, success: bool, operation: str, response_count: int) -> None:
        # Real records are never counted into deception telemetry. Only synthetic rows
        # executed on the honeypot target receive entity counts.
        entity = operation.removeprefix("get_").removeprefix("enumerate_")
        exposed = {entity: response_count} if decision.target == "honeypot" and response_count else {}
        self.decision_client.observe(
            decision=decision,
            success=success,
            exposed_entities=exposed,
            response_count=response_count,
        )
        self._evidence.append(
            {
                "decision_id": decision.decision_id,
                "session_id": decision.session_id,
                "operation": operation,
                "destination": decision.target,
                "risk_score": decision.risk_score,
                "attack_stage": decision.attack_stage,
                "triggered_rules": decision.triggered_rules,
                "success": success,
                "response_count": response_count,
                "recorded_at": self._now(),
            }
        )

    def evidence(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(self._evidence)[-max(1, min(limit, 200)):]

    def login(self, *, email: str, password: str, client_ip: str | None) -> GatewayResult:
        decision = self.decision_client.decide(
            session_id=str(uuid4()), operation="login", client_ip=client_ip
        )
        database = self._database(decision.target)
        response_count = 0
        try:
            with database.transaction() as cursor:
                cursor.execute(
                    database.adapt(
                        "SELECT id, full_name, email, password_hash FROM bank_customers WHERE lower(email) = lower(?)"
                    ),
                    (email.strip(),),
                )
                row = cursor.fetchone()
                if row and verify_password(password, row[3] if not isinstance(row, dict) else row["password_hash"]):
                    customer = self._row(row)
                    response_count = 1
                    self._audit(
                        cursor, database, session_id=decision.session_id, decision=decision,
                        operation="login", success=True, response_count=1,
                        entity_type="customer", entity_count=1 if decision.target == "honeypot" else 0,
                    )
                    result = GatewayResult(True, customer, 1, decision.target, decision)
                else:
                    self._audit(
                        cursor, database, session_id=decision.session_id, decision=decision,
                        operation="login", success=False, response_count=0,
                        entity_type=None, entity_count=0,
                    )
                    result = GatewayResult(False, None, 0, decision.target, decision)
            self._observe(decision=decision, success=result.success, operation="login", response_count=response_count)
            return result
        except GatewayError:
            self._observe(decision=decision, success=False, operation="login", response_count=0)
            raise
        except Exception as exc:
            logger.exception("login database operation failed")
            self._observe(decision=decision, success=False, operation="login", response_count=0)
            raise GatewayDatabaseError() from exc

    def execute(self, *, session: Session, operation: str, payload: dict[str, Any] | None = None, client_ip: str | None = None) -> GatewayResult:
        if operation not in OPERATIONS:
            raise GatewayError("unsupported banking operation")
        payload = payload or {}
        decision = self.decision_client.decide(
            session_id=session.phantom_session_id,
            operation=operation,
            client_ip=client_ip,
        )
        if operation in SENSITIVE_OPERATIONS and decision.target != "honeypot":
            self._observe(decision=decision, success=False, operation=operation, response_count=0)
            raise SensitiveOperationDenied()
        # A deception session can never be promoted into a real-data session by a
        # later low-risk decision. This prevents cross-dataset identity confusion.
        if session.target == "honeypot" and decision.target == "real":
            self._observe(decision=decision, success=False, operation=operation, response_count=0)
            raise SensitiveOperationDenied()

        database = self._database(decision.target)
        customer_id = (
            self._customer_id("honeypot") if decision.target == "honeypot"
            else session.customer_id
        )
        response_count = 0
        result_data: Any = None
        entity_type: str | None = None
        try:
            with database.transaction(immediate=operation == "create_transfer") as cursor:
                if operation == "get_accounts":
                    cursor.execute(database.adapt("SELECT id, account_type, account_number, balance_cents, available_cents, currency, status FROM accounts WHERE customer_id = ? ORDER BY account_type"), (customer_id,))
                    result_data = [self._row(row) for row in cursor.fetchall()]
                    entity_type = "accounts"
                elif operation == "get_balance":
                    cursor.execute(database.adapt("SELECT COALESCE(SUM(balance_cents), 0) AS total_balance_cents, COALESCE(SUM(available_cents), 0) AS total_available_cents FROM accounts WHERE customer_id = ?"), (customer_id,))
                    result_data = self._row(cursor.fetchone()) or {"total_balance_cents": 0, "total_available_cents": 0}
                    entity_type = "balance"
                elif operation == "get_transactions":
                    limit = max(1, min(int(payload.get("limit", 50)), 100))
                    cursor.execute(database.adapt("SELECT id, account_id, direction, amount_cents, merchant, description, category, occurred_at, status, transfer_id FROM transactions WHERE customer_id = ? ORDER BY occurred_at DESC LIMIT ?"), (customer_id, limit))
                    result_data = [self._row(row) for row in cursor.fetchall()]
                    entity_type = "transactions"
                elif operation == "get_beneficiaries":
                    cursor.execute(database.adapt("SELECT id, name, account_hint, bank_name FROM beneficiaries WHERE customer_id = ? ORDER BY name"), (customer_id,))
                    result_data = [self._row(row) for row in cursor.fetchall()]
                    entity_type = "beneficiaries"
                elif operation == "get_cards":
                    cursor.execute(database.adapt("SELECT id, card_name, card_number_masked, card_type, status, expires_on, spending_limit_cents FROM cards WHERE customer_id = ? ORDER BY card_name"), (customer_id,))
                    result_data = [self._row(row) for row in cursor.fetchall()]
                    entity_type = "cards"
                elif operation == "get_profile":
                    cursor.execute(database.adapt("SELECT id, full_name, email, phone, address, created_at FROM bank_customers WHERE id = ?"), (customer_id,))
                    result_data = self._row(cursor.fetchone())
                    entity_type = "profile"
                elif operation == "create_transfer":
                    result_data = self._create_transfer(cursor, database, customer_id, payload)
                    entity_type = "transfers"
                elif operation == "list_tables":
                    if database.is_sqlite:
                        cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
                    else:
                        cursor.execute("SELECT table_name AS name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
                    result_data = [self._row(row)["name"] for row in cursor.fetchall()]
                    entity_type = "tables"
                elif operation == "enumerate_api":
                    result_data = sorted(OPERATIONS)
                    entity_type = "api_operations"
                elif operation == "get_customers":
                    cursor.execute(database.adapt("SELECT id, full_name, email, customer_marker FROM bank_customers ORDER BY full_name"))
                    result_data = [self._row(row) for row in cursor.fetchall()]
                    entity_type = "customers"
                elif operation == "enumerate_accounts":
                    cursor.execute("SELECT id, customer_id, account_number, balance_cents, status FROM accounts ORDER BY id")
                    result_data = [self._row(row) for row in cursor.fetchall()]
                    entity_type = "accounts"
                elif operation == "enumerate_transactions":
                    cursor.execute("SELECT id, customer_id, account_id, amount_cents, occurred_at FROM transactions ORDER BY occurred_at DESC LIMIT 200")
                    result_data = [self._row(row) for row in cursor.fetchall()]
                    entity_type = "transactions"
                elif operation == "probe_admin":
                    result_data = {"status": "not_available", "message": "Administrative access is not exposed."}
                    entity_type = "admin_probe"
                elif operation == "credential_probe":
                    result_data = {"accepted": False, "message": "Credentials are never accepted through this route."}
                    entity_type = "credential_probe"
                else:  # pragma: no cover - allowlist above is exhaustive
                    raise GatewayError("unsupported banking operation")

                if isinstance(result_data, list):
                    response_count = len(result_data)
                elif result_data is None:
                    response_count = 0
                else:
                    response_count = 1
                entity_count = response_count if decision.target == "honeypot" else 0
                self._audit(
                    cursor, database, session_id=decision.session_id, decision=decision,
                    operation=operation, success=True, response_count=response_count,
                    entity_type=entity_type, entity_count=entity_count,
                )
            result = GatewayResult(True, result_data, response_count, decision.target, decision)
            self._observe(decision=decision, success=True, operation=operation, response_count=response_count)
            return result
        except GatewayError:
            self._observe(decision=decision, success=False, operation=operation, response_count=0)
            raise
        except Exception as exc:
            logger.exception("banking database operation %s failed", operation)
            self._observe(decision=decision, success=False, operation=operation, response_count=0)
            raise GatewayDatabaseError() from exc

    def _create_transfer(self, cursor, database: Database, customer_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        source_account_id = str(payload.get("source_account_id", ""))
        beneficiary_id = str(payload.get("beneficiary_id", ""))
        idempotency_key = str(payload.get("idempotency_key", ""))
        amount_cents = int(payload.get("amount_cents", 0))
        reference = str(payload.get("reference", "Transfer"))[:120]
        if not source_account_id or not beneficiary_id or not idempotency_key or amount_cents <= 0:
            raise GatewayConflict()

        # Serialize this customer's transfers before checking idempotency.
        # Locking after the check allows two concurrent requests to both miss
        # the original transfer. SQLite BEGIN IMMEDIATE already serializes.
        if not database.is_sqlite:
            cursor.execute(database.adapt("SELECT id FROM bank_customers WHERE id = ? FOR UPDATE"), (customer_id,))
        cursor.execute(database.adapt("SELECT id, amount_cents, source_account_id, beneficiary_id, reference, created_at FROM transfers WHERE customer_id = ? AND idempotency_key = ?"), (customer_id, idempotency_key))
        existing = cursor.fetchone()
        if existing:
            row = self._row(existing)
            if (int(row["amount_cents"]), row["source_account_id"], row["beneficiary_id"], row["reference"]) != (amount_cents, source_account_id, beneficiary_id, reference):
                raise GatewayConflict()
            return {
                "id": row["id"], "amount_cents": int(row["amount_cents"]),
                "reference": row["reference"], "created_at": row["created_at"],
                "status": "completed", "idempotent_replay": True,
            }

        lock = " FOR UPDATE" if not database.is_sqlite else ""
        cursor.execute(database.adapt(f"SELECT id, balance_cents, available_cents FROM accounts WHERE id = ? AND customer_id = ?{lock}"), (source_account_id, customer_id))
        account = self._row(cursor.fetchone())
        cursor.execute(database.adapt("SELECT id, name FROM beneficiaries WHERE id = ? AND customer_id = ?"), (beneficiary_id, customer_id))
        beneficiary = self._row(cursor.fetchone())
        if not account or not beneficiary or int(account["available_cents"]) < amount_cents:
            raise GatewayConflict()

        transfer_id = str(uuid4())
        now = self._now()
        cursor.execute(database.adapt("UPDATE accounts SET balance_cents = balance_cents - ?, available_cents = available_cents - ? WHERE id = ?"), (amount_cents, amount_cents, source_account_id))
        cursor.execute(database.adapt("INSERT INTO transfers (id, customer_id, source_account_id, beneficiary_id, amount_cents, reference, idempotency_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"), (transfer_id, customer_id, source_account_id, beneficiary_id, amount_cents, reference, idempotency_key, now))
        cursor.execute(database.adapt("INSERT INTO transactions (id, customer_id, account_id, direction, amount_cents, merchant, description, category, occurred_at, status, transfer_id) VALUES (?, ?, ?, 'out', ?, ?, ?, 'transfer', ?, 'completed', ?)"), (str(uuid4()), customer_id, source_account_id, amount_cents, beneficiary["name"], reference, now, transfer_id))
        return {
            "id": transfer_id, "amount_cents": amount_cents, "reference": reference,
            "created_at": now, "status": "completed", "idempotent_replay": False,
        }
