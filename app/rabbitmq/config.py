import os
from typing import Optional
from pydantic_settings import BaseSettings


class RabbitMQConfig(BaseSettings):
    """RabbitMQ configuration settings for Communication Service"""
    
    # Connection settings
    host: str = os.getenv("RABBITMQ_HOST")
    port: int = int(os.getenv("RABBITMQ_PORT"))
    username: str = os.getenv("RABBITMQ_USERNAME")
    password: str = os.getenv("RABBITMQ_PASSWORD")
    virtual_host: str = os.getenv("RABBITMQ_VHOST")
    
    # Connection pool settings
    connection_attempts: int = int(os.getenv("RABBITMQ_CONNECTION_ATTEMPTS", "3"))
    retry_delay: float = float(os.getenv("RABBITMQ_RETRY_DELAY", "2.0"))
    heartbeat: int = int(os.getenv("RABBITMQ_HEARTBEAT", "600"))
    
    # Exchange settings
    otp_exchange: str = "user.otp.exchange"
    exchange_type: str = "topic"
    
    # Queue settings
    email_queue: str = "user.otp.email.queue"
    sms_queue: str = "user.otp.sms.queue"
    
    # Routing keys
    email_routing_key: str = "otp.email.send"
    sms_routing_key: str = "otp.sms.send"
    
    # Message settings
    message_ttl: int = int(os.getenv("RABBITMQ_MESSAGE_TTL", "300000"))  # 5 minutes in milliseconds
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from environment


# Global config instance
rabbitmq_config = RabbitMQConfig()
