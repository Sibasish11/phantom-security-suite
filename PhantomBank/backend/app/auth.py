from __future__ import annotations

from dataclasses import dataclass
from hashlib import pbkdf2_hmac
import base64
import hashlib
import hmac
import secrets
import threading
import time
from uuid import UUID, uuid4

from .config import settings


_PASSWORD_ROUNDS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = pbkdf2_hmac("sha256", password.encode(), salt, _PASSWORD_ROUNDS)
    return "pbkdf2_sha256${}${}${}".format(
        _PASSWORD_ROUNDS,
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode(),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = pbkdf2_hmac(
            "sha256",
            password.encode(),
            base64.urlsafe_b64decode(salt.encode()),
            int(rounds),
        )
        return hmac.compare_digest(
            base64.urlsafe_b64encode(digest).decode(), expected
        )
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class Session:
    session_id: str
    customer_id: str
    full_name: str
    email: str
    target: str
    csrf_token: str
    created_at: float
    expires_at: float
    phantom_session_id: str = ""


class SessionStore:
    """Server-side session state; the cookie contains only a signed opaque UUID."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _signature(session_id: str) -> str:
        digest = hmac.new(
            settings.auth_secret_key.encode(), session_id.encode(), hashlib.sha256
        ).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    def signed_cookie(self, session_id: str) -> str:
        return f"{session_id}.{self._signature(session_id)}"

    def create(
        self,
        *,
        customer_id: str,
        full_name: str,
        email: str,
        target: str,
        phantom_session_id: str,
        session_id: str | None = None,
    ) -> Session:
        now = time.time()
        session = Session(
            session_id=session_id or str(uuid4()),
            customer_id=customer_id,
            full_name=full_name,
            email=email,
            target=target,
            phantom_session_id=phantom_session_id,
            csrf_token=secrets.token_urlsafe(32),
            created_at=now,
            expires_at=now + settings.session_ttl_minutes * 60,
        )
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def _parse(self, cookie: str | None) -> str | None:
        if not cookie or "." not in cookie:
            return None
        session_id, signature = cookie.split(".", 1)
        try:
            UUID(session_id)
        except ValueError:
            return None
        if not hmac.compare_digest(signature, self._signature(session_id)):
            return None
        return session_id

    def get(self, cookie: str | None) -> Session | None:
        session_id = self._parse(cookie)
        if not session_id:
            return None
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            if session.expires_at <= time.time():
                self._sessions.pop(session_id, None)
                return None
            return session

    def revoke(self, cookie: str | None) -> None:
        session_id = self._parse(cookie)
        if session_id:
            with self._lock:
                self._sessions.pop(session_id, None)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


sessions = SessionStore()
