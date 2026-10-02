from functools import lru_cache

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    phantomlayer_url: str = Field(
        default="http://localhost:8000",
        validation_alias="PHANTOMLAYER_URL",
    )

    agent_id: str | None = Field(
        default=None,
        validation_alias="AGENT_ID",
    )

    registration_token: str | None = Field(
        default=None,
        validation_alias="REGISTRATION_TOKEN",
    )

    agent_name: str = Field(
        default="phantomlayer-agent",
        validation_alias="AGENT_NAME",
    )

    agent_version: str = Field(
        default="0.1.0",
        validation_alias="AGENT_VERSION",
    )

    heartbeat_interval_seconds: int = Field(
        default=30,
        ge=5,
        validation_alias="HEARTBEAT_INTERVAL_SECONDS",
    )

    telemetry_batch_size: int = Field(
        default=20,
        ge=1,
        le=100,
        validation_alias="TELEMETRY_BATCH_SIZE",
    )

    real_database_url: str = Field(
        default="",
        validation_alias="REAL_DATABASE_URL",
    )

    honeypot_database_url: str = Field(
        default="",
        validation_alias="HONEYPOT_DATABASE_URL",
    )


@lru_cache
def get_settings() -> AgentSettings:
    return AgentSettings()