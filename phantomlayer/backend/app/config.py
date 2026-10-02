from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PhantomLayer"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    real_database_url: str = (
        "postgresql+psycopg://phantomlayer:phantomlayer"
        "@localhost:5432/phantomlayer_real"
    )

    honeypot_database_url: str = (
        "postgresql+psycopg://phantomlayer:phantomlayer"
        "@localhost:5433/phantomlayer_honeypot"
    )

    control_database_url: str = (
        "postgresql+psycopg://phantomlayer:phantomlayer"
        "@localhost:5434/phantomlayer_control"
    )

    auth_secret_key: str = ""
    auth_access_token_expire_minutes: int = 60
    auth_algorithm: str = "HS256"

    # Development-only demo controls.
    demo_mode: bool = False

    @model_validator(mode="after")
    def validate_security_defaults(self):
        if (len(self.auth_secret_key) < 32 or
                self.auth_secret_key.startswith("generate-a-long-random")):
            raise ValueError("AUTH_SECRET_KEY must be a unique random secret of at least 32 characters")
        if self.auth_access_token_expire_minutes < 5:
            raise ValueError("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES must be at least 5")
        return self

    @field_validator("debug", "demo_mode", mode="before")
    @classmethod
    def parse_boolean_environment(cls, value):
        """Accept common boolean and deployment labels."""
        if isinstance(value, str):
            normalized = value.strip().lower()

            if normalized in {
                "true",
                "1",
                "yes",
                "on",
                "development",
                "dev",
            }:
                return True

            if normalized in {
                "false",
                "0",
                "no",
                "off",
                "release",
                "production",
                "prod",
            }:
                return False

        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()