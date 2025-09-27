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

    # Email SMTP Settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    gmail_username: str 
    gmail_app_password: str

    # Redis/Celery Settings
    redis_host: str
    redis_port: int
    redis_password: Optional[str] = None
    redis_db: int = 0
    redis_max_connections: int = 20
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5

    # Construct Redis URLs dynamically
    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url

    # Logging Settings
    logs_directory: str = "app/logs"
    sms_log_file: str = "sms_logs.csv"
    email_log_file: str = "email_logs.csv"
    log_retention_days: int = 7
    log_level: str = "INFO"

    # SMS Service Performance Settings
    sms_rate_limit: int = 10  # Max concurrent SMS requests
    sms_timeout: float = 30.0  # Request timeout in seconds
    sms_retry_attempts: int = 3  # Number of retry attempts
    sms_circuit_breaker_threshold: int = 5  # Failures before circuit breaker opens
    sms_circuit_breaker_timeout: int = 60  # Circuit breaker timeout in seconds

    # Email Service Performance Settings
    email_rate_limit: int = 5  # Max concurrent email requests
    email_retry_attempts: int = 3  # Number of retry attempts
    email_circuit_breaker_threshold: int = 3  # Failures before circuit breaker opens
    email_circuit_breaker_timeout: int = 60  # Circuit breaker timeout in seconds

    # HTTP Client Settings
    http_max_connections: int = 100
    http_max_keepalive_connections: int = 20
    http_connect_timeout: float = 10.0

    # CORS Settings
    cors_origins: str = "http://localhost:3000,http://localhost:8080,http://localhost:8002"

    # RabbitMQ Settings
    rabbitmq_host: str
    rabbitmq_port: int
    rabbitmq_username: str
    rabbitmq_password: str
    rabbitmq_vhost: str = "/"
    rabbitmq_connection_attempts: int = 3
    rabbitmq_retry_delay: float = 2.0
    rabbitmq_heartbeat: int = 600
    rabbitmq_message_ttl: int = 300000

    # RabbitMQ Queue Settings
    otp_exchange: str = "user.otp.exchange"
    email_queue: str = "user.otp.email.queue"
    sms_queue: str = "user.otp.sms.queue"
    email_routing_key: str = "otp.email.send"
    sms_routing_key: str = "otp.sms.send"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from environment


settings = Settings()
