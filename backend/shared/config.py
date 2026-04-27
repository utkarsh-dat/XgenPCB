"""
PCB Builder - Shared Configuration
Central configuration management using pydantic-settings.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Application ──────────────────────────────────────────
    app_env: str = "development"
    app_debug: bool = True
    app_port: int = 8000
    app_title: str = "PCB Builder API"
    app_version: str = "0.1.0"

    # ── Database ─────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "pcbbuilder"
    postgres_user: str = "pcbbuilder"
    postgres_password: str = "pcbbuilder_dev"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── Redis ────────────────────────────────────────────────
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    redis_url: str = "redis://redis:6379/0"

    # ── Auth ─────────────────────────────────────────────────
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""

    # ── AI / LLM ─────────────────────────────────────────────
    openai_api_key: str = ""
    llm_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # ── NVIDIA NIM ────────────────────────────────────────────
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"

    # ── S3 / Object Storage ──────────────────────────────────
    s3_bucket: str = "pcb-builder-assets"
    s3_region: str = "ap-south-1"
    s3_endpoint_url: Optional[str] = "http://localhost:9000"
    aws_access_key_id: str = "minioadmin"
    aws_secret_access_key: str = "minioadmin"

    # ── Local Storage ────────────────────────────────────────
    local_storage_path: str = "./storage/designs"

    # Storage path for designs

    # ── Stripe ───────────────────────────────────────────────
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_team: str = ""

    # ── Email ────────────────────────────────────────────────
    sendgrid_api_key: str = ""
    from_email: str = "noreply@pcbbuilder.ai"

    # ── CORS ─────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ── Elasticsearch ────────────────────────────────────────
    elasticsearch_host: str = "localhost"
    elasticsearch_port: int = 9200

    @property
    def elasticsearch_url(self) -> str:
        return f"http://{self.elasticsearch_host}:{self.elasticsearch_port}"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
