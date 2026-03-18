from pydantic import BaseSettings, validator
from typing import List, Optional, Union
import secrets


class Settings(BaseSettings):
    # Project Configuration
    PROJECT_NAME: str = "FastAPI XGBoost Optimizer"
    PROJECT_DESCRIPTION: str = "AI-powered optimization service combining XGBoost, genetic algorithms, and constraint programming"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_HOSTS: List[str] = ["*"]

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Security Configuration
    REQUIRE_API_KEY: bool = True
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Database Configuration
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/optimizer"
    POSTGIS_EXTENSIONS: List[str] = ["postgis", "postgis_topology"]

    # Hasura Configuration
    HASURA_URL: str = "http://localhost:8080/v1/graphql"
    HASURA_ADMIN_SECRET: str = "admin-secret"

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 3600  # 1 hour

    # XGBoost Configuration
    XGBOOST_MODEL_PATH: str = "/app/models"
    XGBOOST_PARAMETERS: dict = {
        "objective": "reg:squarederror",
        "max_depth": 6,
        "eta": 0.3,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
    }

    # PyGAD Configuration
    PYGAD_POPULATION_SIZE: int = 100
    PYGAD_NUM_GENERATIONS: int = 200
    PYGAD_MUTATION_RATE: float = 0.1
    PYGAD_CROSSOVER_RATE: float = 0.9

    # OR-Tools Configuration
    ORTOOLS_MAX_TIME: int = 300  # 5 minutes
    ORTOOLS_NUM_SOLUTIONS: int = 10

    # Rate Limiting
    RATE_LIMIT: int = 100  # requests per minute
    BURST_LIMIT: int = 200

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Monitoring Configuration
    PROMETHEUS_PORT: int = 9090
    GRAFANA_PORT: int = 3000

    class Config:
        case_sensitive = True
        env_file = ".env"


# Create global settings instance
settings = Settings()
