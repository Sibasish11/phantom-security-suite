"""
Phase 11 – AI Incident Analysis: Configuration

All secrets are read from the environment.  Nothing is hardcoded.
The application will NOT expose these values in API responses or logs.
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    """
    Settings for the AI Incident Analysis module.

    Environment variables (case-insensitive via pydantic-settings):
        AI_ENABLED          – Master switch.  Defaults to False so the system
                              works out-of-the-box without any API key.
        AI_PROVIDER         – "mock" (default), "openai", "anthropic", etc.
                              Only "mock" is implemented in Phase 11.
        AI_MODEL            – Model identifier for the chosen provider.
        AI_API_KEY          – Secret API key.  Never logged or returned by any
                              API endpoint.
        AI_TIMEOUT_SECONDS  – Per-request timeout for AI calls (seconds).
        AI_MAX_TIMELINE_STEPS
                            – Maximum timeline steps to include in the
                              sanitized payload sent to the AI (guards against
                              very long sessions exceeding context windows).
    """

    ai_enabled: bool = Field(default=False, description="Enable AI analysis")
    ai_provider: str = Field(default="mock", description="AI provider name")
    ai_model: str = Field(default="mock-model-v1", description="Model identifier")
    ai_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Provider API key – never exposed in responses or logs",
    )
    ai_timeout_seconds: int = Field(default=30, ge=1, le=300)
    ai_max_timeline_steps: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Truncate timelines longer than this before sending to AI",
    )

    model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
    env_prefix="",
    extra="ignore",
)


ai_settings = AISettings()
