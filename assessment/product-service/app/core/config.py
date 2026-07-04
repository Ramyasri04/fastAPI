from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Product Service"
    ENVIRONMENT: str = "development"
    
    # Postgres
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # JWT Auth Validation
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
