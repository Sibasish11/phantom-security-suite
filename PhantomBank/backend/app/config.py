from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PhantomBank"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8001
    real_database_url: str = "postgresql://phantombank:change-me@localhost:55432/phantombank_real"
    honeypot_database_url: str = "postgresql://phantombank:change-me@localhost:55433/phantombank_honeypot"
    auth_secret_key: str = ""
    session_ttl_minutes: int = 60
    cookie_secure: bool = False
    allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
    phantomlayer_url: str = "http://backend:8000"
    agent_id: str = ""
    agent_token: str = ""
    phantomlayer_timeout_seconds: float = 4.0
    defender_evidence_token: str = ""
    demo_mode: bool = True

    @model_validator(mode="after")
    def validate_secrets(self):
        if len(self.auth_secret_key) < 32 or self.auth_secret_key.startswith('replace-with-'):
            raise ValueError('Set a random AUTH_SECRET_KEY of at least 32 characters')
        if self.real_database_url == self.honeypot_database_url:
            raise ValueError('Real and deception database URLs must differ')
        return self

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("debug", "cookie_secure", "demo_mode", mode="before")
    @classmethod
    def parse_boolean(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

REAL_CUSTOMER_ID = "real-customer-maya-001"
HONEYPOT_CUSTOMER_ID = "decoy-customer-john-991"
