"""Authentication boundary regressions run against the isolated QA database."""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


client = TestClient(app)


def _login() -> str:
    response = client.post(
        "/auth/login",
        json={
            "email": "login-test@example.com",
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_valid_token_can_access_tenant_dashboard():
    token = _login()
    response = client.get(
        "/security/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_expired_token_is_401_not_500():
    valid_token = _login()
    claims = jwt.decode(valid_token, options={"verify_signature": False})
    claims["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    expired = jwt.encode(claims, settings.auth_secret_key, algorithm=settings.auth_algorithm)

    response = client.get(
        "/security/stats",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired authentication token"


def test_missing_token_is_401():
    response = client.get("/security/stats")
    assert response.status_code == 401
