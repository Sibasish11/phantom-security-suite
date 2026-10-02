"""Configuration shape for the customer-run PhantomLayer agent.

This is intentionally local-only.  Its secrets are read from the customer's
environment or secret manager and are never serialized to the control plane.
"""
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LocalAgentSettings(BaseSettings):
    agent_name: str
    control_plane_url: str
    agent_registration_token: SecretStr
    real_database_url: SecretStr
    honeypot_database_url: SecretStr
    telemetry_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, env_prefix="PHANTOMLAYER_AGENT_")
