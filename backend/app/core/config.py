import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core Application Settings
    ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    PROJECT_NAME: str = Field(default="QueryPilot")
    SECRET_KEY: str = Field(default="supersecretkeychangeinproductionjwtgeneration")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)
    
    # API CORS origins
    BACKEND_CORS_ORIGINS: List[str] = Field(default=["*"])

    # FastAPI Server settings
    BACKEND_HOST: str = Field(default="0.0.0.0")
    BACKEND_PORT: int = Field(default=8000)

    # Cache Settings
    REDIS_URL: Optional[str] = Field(default=None)

    # Databases Configuration
    # Fallback to local sqlite database files for testing if URLs are not provided
    DATABASE_URL: str = Field(default="sqlite:///./querypilot_app.db")
    EXECUTION_DB_ADMIN_URL: str = Field(default="sqlite:///./querypilot_execution.db")
    EXECUTION_DB_READONLY_URL: str = Field(default="sqlite:///./querypilot_execution.db")

    # LLM Keys
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)

    # LLM Defaults
    DEFAULT_LLM_PROVIDER: str = Field(default="mock")
    DEFAULT_LLM_MODEL: str = Field(default="mock-model")

    # Clarification Defaults
    AMBIGUITY_THRESHOLD: float = Field(default=0.7)
    MAX_CLARIFICATION_ROUNDS: int = Field(default=2)
    MAX_REPAIR_ATTEMPTS: int = Field(default=3)

    # Query Safety Limits
    QUERY_TIMEOUT_SECONDS: int = Field(default=5)
    MAX_EXECUTION_ROWS: int = Field(default=500)

settings = Settings()
