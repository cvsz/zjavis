"""Application configuration management.

Uses pydantic-settings for type-safe, environment-driven configuration.
All values have safe defaults; secrets must never be hardcoded.
"""

from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment variables are read with the ``JARVIS_`` prefix.
    Example: ``JARVIS_APP_ENV=development``.
    """

    model_config = SettingsConfigDict(
        env_prefix="JARVIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    # --- Application -------------------------------------------------------
    app_name: str = Field(default="jarvis", description="Application name")
    app_env: str = Field(
        default="development",
        description="Deployment environment: development, staging, production",
    )
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="info", description="Log level")

    # --- Server ------------------------------------------------------------
    host: str = Field(default="127.0.0.1", description="Bind host")
    port: int = Field(default=8000, description="Bind port")
    workers: int = Field(default=1, description="Number of worker processes")

    # --- Database ----------------------------------------------------------
    database_url: str = Field(
        default="postgresql+psycopg://jarvis:jarvis@localhost:5432/jarvis",
        description="PostgreSQL connection URL",
    )
    database_echo: bool = Field(
        default=False, description="Enable SQL statement logging"
    )
    database_pool_size: int = Field(
        default=10, description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=20, description="Database max overflow connections"
    )

    # --- Security ----------------------------------------------------------
    app_secret: str = Field(
        default="dev-secret-change-me-in-production",
        description="Secret key for signing tokens and sessions. "
        "Must be set via JARVIS_APP_SECRET in production.",
    )

    @model_validator(mode="after")
    def _validate_production_secret(self) -> Settings:
        """Fail closed in production if the default secret key is used."""
        if self.app_env == "production" and self.app_secret == "dev-secret-change-me-in-production":
            raise ValueError(
                "JARVIS_APP_SECRET must be set when JARVIS_APP_ENV=production"
            )
        return self
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    algorithm: str = Field(
        default="HS256", description="JWT signing algorithm"
    )

    # --- AI / Model Gateway ------------------------------------------------
    model_gateway_enabled: bool = Field(
        default=True, description="Enable the model gateway"
    )
    cloud_fallback_enabled: bool = Field(
        default=False,
        description="Allow cloud model fallback (disabled by default per blueprint)",
    )
    default_provider: str = Field(
        default="local",
        description="Default model provider",
    )
    default_model: str = Field(
        default="local-model",
        description="Default model name",
    )
    max_tokens: int = Field(
        default=4096, description="Default max tokens per request"
    )
    request_timeout_seconds: int = Field(
        default=120, description="Default model request timeout in seconds"
    )

    # --- Feature flags -----------------------------------------------------
    voice_enabled: bool = Field(
        default=False, description="Enable voice interface (requires hardware)"
    )
    vision_enabled: bool = Field(
        default=False, description="Enable vision interface"
    )
    agent_runtime_enabled: bool = Field(
        default=True, description="Enable agent runtime"
    )
    smart_environment_enabled: bool = Field(
        default=False, description="Enable smart environment integration"
    )


settings = Settings()
