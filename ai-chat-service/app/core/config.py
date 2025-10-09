# app/core/config.py
"""
Configuration management for AI Search System
Environment-based configuration with sensible defaults
"""

import os
from functools import lru_cache
from typing import Optional
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
env_file = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_file)


def get_llm_provider() -> str:
    """Get the LLM provider type (runpod or ollama)."""
    return os.getenv("LLM_PROVIDER", "runpod").lower()


class Settings(BaseSettings):
    """Application settings with environment variable support
    Provider configs (API keys, timeouts, etc) are loaded from environment variables or .env file.
    Use get_settings() to access per-environment config.
    Example usage for providers:
        brave_search_api_key: str = ...
        scrapingbee_api_key: str = ...
    """

    # Application
    app_name: str = "AI Search System"
    debug: bool = False
    environment: str = "development"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    allowed_origins: list[str] = Field(
        default_factory=lambda: (
            os.getenv(
                "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000"
            ).split(",")
            if os.getenv("ALLOWED_ORIGINS")
            else ["http://localhost:3000", "http://localhost:8000"]
        )
    )

    # LLM Provider Configuration
    llm_provider: str = Field(default_factory=lambda: get_llm_provider())

    # RunPod Configuration
    runpod_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("RUNPOD_API_KEY")
    )
    runpod_endpoint_id: str = Field(
        default_factory=lambda: os.getenv("RUNPOD_ENDPOINT_ID", "p94hyu5zhxdl82")
    )
    runpod_base_url: str = "https://api.runpod.ai/v2"
    runpod_timeout: int = 60
    runpod_max_retries: int = 3

    # Legacy Ollama Configuration (for backward compatibility)
    ollama_host: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434")
    )
    ollama_timeout: int = 60
    ollama_max_retries: int = 3

    # Redis Configuration
    redis_url: str = Field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379")
    )
    redis_max_connections: int = 20
    redis_timeout: int = 5

    # Document Search Service Configuration
    document_search_url: str = Field(
        default_factory=lambda: os.getenv("DOCUMENT_SEARCH_URL", "http://localhost:8001")
    )

    # Model Configuration
    default_model: str = "tinyllama:latest"
    fallback_model: str = "tinyllama:latest"
    max_concurrent_models: int = 3
    model_memory_threshold: float = 0.8

    # Cost & Budget Configuration
    cost_per_api_call: float = 0.008
    default_monthly_budget: float = 20.0
    cost_tracking_enabled: bool = True

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10

    # Cache Configuration
    cache_ttl_default: int = 3600  # 1 hour
    cache_ttl_routing: int = 300  # 5 minutes
    cache_ttl_responses: int = 1800  # 30 minutes

    # Performance Targets
    target_response_time: float = 2.5
    target_local_processing: float = 0.85
    target_cache_hit_rate: float = 0.80

    # LangGraph Configuration
    graph_max_iterations: int = 50
    graph_timeout: int = 30
    graph_retry_attempts: int = 2

    # External APIs
    brave_search_api_key: Optional[str] = None
    zerows_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text

    # Security
    jwt_secret_key: str = Field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY", os.urandom(32).hex())
    )
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # Database (for future use)
    database_url: Optional[str] = None
    
    # Security Configuration
    encryption_master_key: Optional[str] = None
    config_master_key: Optional[str] = None
    audit_secret_key: Optional[str] = None
    
    # Data Protection Settings
    enable_data_encryption: bool = True
    enable_audit_logging: bool = True
    enable_gdpr_compliance: bool = True
    enable_key_rotation: bool = True
    
    # TLS/SSL Settings
    tls_enabled: bool = Field(
        default_factory=lambda: os.getenv("TLS_ENABLED", "false").lower() == "true"
    )
    server_ssl_cert: Optional[str] = None
    server_ssl_key: Optional[str] = None
    server_ca_cert: Optional[str] = None
    ssl_cert_dir: str = "/etc/ssl/certs"
    
    # Redis TLS Configuration
    redis_tls_enabled: bool = Field(
        default_factory=lambda: os.getenv("REDIS_TLS_ENABLED", "false").lower() == "true"
    )
    redis_ca_cert: Optional[str] = None
    redis_client_cert: Optional[str] = None
    redis_client_key: Optional[str] = None
    
    # ClickHouse TLS Configuration
    clickhouse_tls_enabled: bool = Field(
        default_factory=lambda: os.getenv("CLICKHOUSE_TLS_ENABLED", "false").lower() == "true"
    )
    clickhouse_ca_cert: Optional[str] = None
    clickhouse_client_cert: Optional[str] = None
    clickhouse_client_key: Optional[str] = None
    
    # Data Retention Settings
    conversation_retention_days: int = 365
    analytics_retention_days: int = 730
    audit_log_retention_days: int = 2555  # 7 years
    session_retention_hours: int = 24
    
    # Consent Management
    default_consent_expiry_days: int = 365
    consent_withdrawal_grace_days: int = 30
    
    # Key Rotation Settings
    key_rotation_check_interval_minutes: int = 60
    confidential_key_rotation_days: int = 90
    restricted_key_rotation_days: int = 30
    
    # Security Headers
    enable_security_headers: bool = True
    enable_hsts: bool = True
    hsts_max_age: int = 31536000  # 1 year
    enable_csp: bool = True
    csp_policy: Optional[str] = None
    
    # Model configuration to enable loading from .env files
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }

    # New search provider settings
    BRAVE_API_KEY: Optional[str] = None
    SCRAPINGBEE_API_KEY: Optional[str] = None
    # Performance settings
    CACHE_TTL: int = 3600
    MAX_CACHE_SIZE: int = 50000
    PERFORMANCE_MONITORING: bool = True
    # Search settings
    DEFAULT_SEARCH_BUDGET: float = 2.0
    DEFAULT_QUALITY_REQUIREMENT: str = "standard"
    MAX_SEARCH_RESULTS: int = 10
    
    # Document search configuration
    enable_web_search_in_documents: bool = Field(
        default=False,
        description="Enable web search in document search service"
    )
    
    # Research configuration
    enable_web_search_in_research: bool = Field(
        default=True,
        description="Enable web search in research deep-dive workflows"
    )

    # Model configuration to enable loading from .env files
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


class DevelopmentSettings(Settings):
    """Development environment settings"""

    debug: bool = True
    log_level: str = "DEBUG"
    environment: str = "development"


class ProductionSettings(Settings):
    """Production environment settings"""

    debug: bool = False
    log_level: str = "INFO"
    environment: str = "production"

    # More restrictive settings for production
    redis_max_connections: int = 50
    rate_limit_per_minute: int = 100
    target_response_time: float = 2.0


class TestingSettings(Settings):
    """Testing environment settings"""

    debug: bool = True
    environment: str = "testing"
    # Use in-memory or test databases
    # Use env var if set, else default
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/1")
    # Faster timeouts for tests
    ollama_timeout: int = 10
    redis_timeout: int = 1
    graph_timeout: int = 5


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    import os

    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment == "production":
        return ProductionSettings()
    elif environment == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


# Model configuration constants
MODEL_ASSIGNMENTS = {
    # Original chat/search tasks
    "simple_classification": "phi3:mini",
    "qa_and_summary": "phi3:mini",
    "analytical_reasoning": "llama3:8b",
    "deep_research": "llama3:8b",
    "code_tasks": "phi3:mini",
    "multilingual": "llama3:8b",
    "creative_writing": "llama3:8b",
    "conversation": "llama3:8b",
    # Recruitment-specific tasks
    "resume_parsing": "deepseek-llm:7b",
    "bias_detection": "mistral:7b",
    "matching_logic": "llama3:8b",
    "conversational_script_generation": "llama3:8b",
    "report_generation": "phi3:mini",
    # Recruitment workflow aliases
    "parsing": "deepseek-llm:7b",
    "bias_check": "mistral:7b",
    "matching": "llama3:8b",
    "script_gen": "llama3:8b",
    "summary_report": "phi3:mini",
}

PRIORITY_TIERS = {
    "T0": ["phi3:mini"],  # Always loaded (2GB) - reports/simple tasks
    "T1": [
        "deepseek-llm:7b",
        "mistral:7b",
    ],  # Keep warm (14GB) - frequent parsing/bias detection
    "T2": ["llama3:8b"],  # Load on demand (8GB) - reasoning/matching tasks
    "T3": ["tinyllama:latest"],  # Cold storage - fallback model
}

# API costs (in INR)
API_COSTS = {
    "phi3:mini": 0.0,
    "deepseek-llm:7b": 0.0,
    "mistral": 0.0,
    "llama3": 0.0,
    "llama2:7b": 0.0,
    "mistral:7b": 0.0,
    "gpt-4": 0.06,
    "claude-haiku": 0.01,
    "brave_search": 0.008,
    "zerows_scraping": 0.02,
}

# Model memory requirements (GB) for A5000 optimization
MODEL_MEMORY_REQUIREMENTS = {
    "phi3:mini": 2,
    "deepseek-llm:7b": 7,
    "mistral": 7,
    "llama3": 8,
    "qwen2.5:0.5b": 0.5,  # Ultra-fast model from router
}

# A5000 memory configuration
A5000_CONFIG = {
    "total_vram_gb": 24,
    "system_reserve_gb": 4,
    "available_vram_gb": 20,
    "max_concurrent_models": 3,
    "preload_threshold_gb": 16,  # Start unloading if above this
}

# Rate limits by tier
RATE_LIMITS = {
    "free": {"requests_per_minute": 1000, "cost_per_month": 20.0},
    "pro": {"requests_per_minute": 10000, "cost_per_month": 500.0},
    "enterprise": {"requests_per_minute": 100000, "cost_per_month": 5000.0},
}
