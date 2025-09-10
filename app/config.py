"""Configuration management for Austin ATAK integrations."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # CoT/TLS Configuration
    cot_url: str = Field(..., env="COT_URL", description="TAK Server CoT URL (tcp://host:port or tls://host:port)")
    pytak_tls_client_cert: Optional[str] = Field(None, env="PYTAK_TLS_CLIENT_CERT", description="Path to client certificate (required for TLS)")
    pytak_tls_client_cert_password: Optional[str] = Field(None, env="PYTAK_TLS_CLIENT_CERT_PASSWORD", description="Client certificate password (required for TLS)")
    pytak_tls_ca: Optional[str] = Field(None, env="PYTAK_TLS_CA", description="Path to CA certificate (required for TLS)")
    
    # SODA API Configuration
    soda_app_token: Optional[str] = Field(None, env="SODA_APP_TOKEN", description="Socrata App Token for rate limiting")
    fire_dataset: str = Field("wpu4-x69d", env="FIRE_DATASET", description="Fire incidents dataset ID")
    traffic_dataset: str = Field("dx9v-zd7x", env="TRAFFIC_DATASET", description="Traffic incidents dataset ID")
    
    # Polling Configuration
    poll_seconds: int = Field(45, env="POLL_SECONDS", description="Polling interval in seconds")
    cot_stale_minutes: int = Field(10, env="COT_STALE_MINUTES", description="CoT stale time in minutes")
    
    # Database Configuration
    database_url: str = Field("sqlite:///./app/store/seen.db", env="DATABASE_URL", description="Database URL for deduplication")
    
    # API Configuration
    api_host: str = Field("0.0.0.0", env="API_HOST", description="API host")
    api_port: int = Field(8080, env="API_PORT", description="API port")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
