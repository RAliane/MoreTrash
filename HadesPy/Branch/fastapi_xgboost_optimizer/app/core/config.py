"""
Application configuration management using Pydantic BaseSettings.

This module provides centralized configuration management with environment
variable support, validation, and type safety for all application settings.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    All settings can be overridden using environment variables with the
    same name, prefixed by the environment prefix (default: "FASTAPI_").
    """
    
    # Application Configuration
    APP_NAME: str = "FastAPI XGBoost Optimizer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    
    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=1, description="Number of worker processes")
    
    # Security Configuration
    SECRET_KEY: str = Field(description="Secret key for encryption")
    API_KEY_HEADER: str = Field(default="X-API-Key", description="API key header name")
    ALLOWED_API_KEYS: List[str] = Field(default_factory=list, description="Allowed API keys")
    
    # Rate Limiting
    RATE_LIMIT: str = Field(default="100/minute", description="Rate limit string")
    RATE_LIMIT_BURST: int = Field(default=10, description="Rate limit burst size")
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    
    # Database Configuration
    DATABASE_URL: str = Field(description="PostgreSQL database URL")
    DATABASE_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=0, description="Database max overflow")
    DATABASE_POOL_TIMEOUT: int = Field(default=30, description="Database pool timeout")
    
    # PostGIS Configuration
    POSTGIS_SRID: int = Field(default=4326, description="Default PostGIS SRID")
    POSTGIS_INDEX_TYPE: str = Field(default="GIST", description="PostGIS index type")
    
    # Hasura Configuration
    HASURA_URL: str = Field(description="Hasura GraphQL endpoint URL")
    HASURA_ADMIN_SECRET: str = Field(description="Hasura admin secret")
    
    # Redis Configuration
    REDIS_URL: str = Field(default="redis://localhost:6379", description="Redis URL")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    
    # XGBoost Configuration
    XGBOOST_MODEL_PATH: str = Field(default="./models/xgboost", description="XGBoost model directory")
    XGBOOST_N_ESTIMATORS: int = Field(default=100, description="Number of estimators")
    XGBOOST_MAX_DEPTH: int = Field(default=6, description="Maximum tree depth")
    XGBOOST_LEARNING_RATE: float = Field(default=0.1, description="Learning rate")
    XGBOOST_SUBSAMPLE: float = Field(default=0.8, description="Subsample ratio")
    XGBOOST_COLSAMPLE_BYTREE: float = Field(default=0.8, description="Column sample ratio")
    
    # PyGAD Configuration
    PYGAD_POPULATION_SIZE: int = Field(default=100, description="Population size")
    PYGAD_NUM_GENERATIONS: int = Field(default=50, description="Number of generations")
    PYGAD_PARENT_SELECTION_TYPE: str = Field(default="tournament", description="Parent selection type")
    PYGAD_CROSSOVER_TYPE: str = Field(default="single_point", description="Crossover type")
    PYGAD_MUTATION_TYPE: str = Field(default="random", description="Mutation type")
    PYGAD_MUTATION_PERCENT_GENES: float = Field(default=10.0, description="Mutation percentage")
    
    # OR-Tools Configuration
    ORTOOLS_MAX_TIME: int = Field(default=30, description="Maximum solver time in seconds")
    ORTOOLS_NUM_SEARCH_WORKERS: int = Field(default=4, description="Number of search workers")
    ORTOOLS_ENABLE_LNS: bool = Field(default=True, description="Enable Large Neighborhood Search")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json or text)")
    LOG_FILE: Optional[str] = Field(default=None, description="Log file path")
    
    # Monitoring Configuration
    METRICS_ENABLED: bool = Field(default=True, description="Enable metrics collection")
    METRICS_PORT: int = Field(default=9090, description="Metrics server port")
    HEALTH_CHECK_ENABLED: bool = Field(default=True, description="Enable health checks")
    
    # Workflow Configuration
    WORKFLOW_TIMEOUT: int = Field(default=300, description="Workflow timeout in seconds")
    MICROTASK_RETRY_ATTEMPTS: int = Field(default=3, description="Microtask retry attempts")
    MICROTASK_RETRY_DELAY: int = Field(default=1, description="Microtask retry delay in seconds")
    
    # Constraint Configuration
    CONSTRAINT_VALIDATION_ENABLED: bool = Field(default=True, description="Enable constraint validation")
    SPATIAL_CONSTRAINT_INDEX: bool = Field(default=True, description="Use spatial indexes")
    
    # Validation
    @validator("SECRET_KEY", pre=True)
    def validate_secret_key(cls, v: Optional[str]) -> str:
        """Validate that secret key is provided."""
        if not v:
            raise ValueError("SECRET_KEY must be provided")
        return v
    
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v: Optional[str]) -> str:
        """Validate database URL."""
        if not v:
            raise ValueError("DATABASE_URL must be provided")
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_API_KEYS", pre=True)
    def parse_api_keys(cls, v: Any) -> List[str]:
        """Parse API keys from string or list."""
        if isinstance(v, str):
            return [key.strip() for key in v.split(",")]
        return v
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_config_dir() -> Path:
    """Get the configuration directory."""
    return get_project_root() / "config"


def get_models_dir() -> Path:
    """Get the models directory."""
    return get_project_root() / "models"


def get_logs_dir() -> Path:
    """Get the logs directory."""
    return get_project_root() / "logs"


# Create directories if they don't exist
for directory in [get_models_dir(), get_logs_dir()]:
    directory.mkdir(exist_ok=True)