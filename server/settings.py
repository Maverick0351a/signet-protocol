#!/usr/bin/env python3
"""
Signet Protocol Settings

Configuration management for the Signet Protocol server.
Supports environment variables and production deployment.
"""

import os
from typing import Optional, List
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Server configuration
    host: str = Field(default="0.0.0.0", env="SIGNET_HOST")
    port: int = Field(default=8088, env="SIGNET_PORT")
    debug: bool = Field(default=False, env="SIGNET_DEBUG")
    
    # Database configuration
    database_url: str = Field(
        default="sqlite:///./signet.db",
        env="DATABASE_URL"
    )
    
    # Redis configuration (optional)
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # Cryptographic keys
    private_key: str = Field(
        default="demo_private_key_change_in_production",
        env="SIGNET_PRIVATE_KEY"
    )
    
    # External service configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    stripe_api_key: Optional[str] = Field(default=None, env="STRIPE_API_KEY")
    
    # Policy configuration
    allowed_hosts: List[str] = Field(
        default=["api.openai.com", "api.anthropic.com"],
        env="SIGNET_ALLOWED_HOSTS"
    )
    
    # Billing configuration
    enable_billing: bool = Field(default=True, env="SIGNET_ENABLE_BILLING")
    default_vex_limit: int = Field(default=1000, env="SIGNET_DEFAULT_VEX_LIMIT")
    default_fu_limit: int = Field(default=5000, env="SIGNET_DEFAULT_FU_LIMIT")
    
    # Security configuration
    max_payload_size: int = Field(default=10_000_000, env="SIGNET_MAX_PAYLOAD_SIZE")  # 10MB
    max_response_size: int = Field(default=50_000_000, env="SIGNET_MAX_RESPONSE_SIZE")  # 50MB
    request_timeout: int = Field(default=30, env="SIGNET_REQUEST_TIMEOUT")  # seconds
    
    # Monitoring configuration
    enable_metrics: bool = Field(default=True, env="SIGNET_ENABLE_METRICS")
    log_level: str = Field(default="INFO", env="SIGNET_LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings (useful for testing)"""
    global _settings
    _settings = None
    return get_settings()