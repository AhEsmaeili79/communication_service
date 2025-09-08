import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # FastAPI Settings
    app_name: str = "Communication Service"
    app_version: str = "1.0.0"
    debug: bool = True

    # SMS API Settings
    sms_api_url: str
    sms_api_key: str
    sms_from_number: str

    # Email Settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    gmail_username: Optional[str] = None
    gmail_app_password: Optional[str] = None

    # Redis/Celery Settings
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Logging Settings
    logs_directory: str = "app/logs"
    sms_log_file: str = "sms_logs.csv"
    email_log_file: str = "email_logs.csv"
    log_retention_days: int = 7

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
