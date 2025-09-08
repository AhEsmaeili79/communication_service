from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "communication_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.core.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.core.tasks.send_sms_task": {"queue": "sms"},
        "app.core.tasks.cleanup_logs_task": {"queue": "maintenance"},
    },
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
)

if __name__ == "__main__":
    celery_app.start()
