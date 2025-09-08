import asyncio
import logging

from app.core.celery_app import celery_app
from app.services.sms.sms_service import sms_service, SMSServiceError
from app.schemas.sms_schema import SMSRequest
from app.utils.csv_logger import cleanup_all_logs

# Configure logging (fallback to standard logging if structlog not available)
try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.core.tasks.send_sms_task")
def send_sms_task(self, sms_data: dict) -> dict:
    """
    Task to send SMS with error handling
    """
    try:
        sms_request = SMSRequest(**sms_data)

        # Handle event loop safely
        try:
            # Try to get existing loop
            loop = asyncio.get_running_loop()
            # If we get here, there's a running loop, so we need to run the coroutine differently
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, sms_service.send_sms(sms_request))
                result = future.result()
        except RuntimeError:
            # No running loop, safe to create new one
            result = asyncio.run(sms_service.send_sms(sms_request))

        logger.info("SMS task completed successfully",
                   task_id=self.request.id,
                   rec_id=result.recId,
                   to=result.to)

        return {
            "recId": result.recId,
            "status": result.status,
            "sent_at": result.sent_at.isoformat(),
            "to": result.to,
            "text": result.text,
            "from_number": result.from_number
        }

    except SMSServiceError as e:
        logger.error("SMS service error in task",
                    task_id=self.request.id,
                    error=str(e),
                    to=sms_data.get("to", ""))
        return {
            "recId": 0,
            "status": f"SMS Service Error: {str(e)}",
            "sent_at": None,
            "to": sms_data.get("to", ""),
            "text": sms_data.get("text", ""),
            "from_number": sms_data.get("from_number", "")
        }
    except Exception as e:
        logger.error("Unexpected error in SMS task",
                    task_id=self.request.id,
                    error=str(e),
                    to=sms_data.get("to", ""))
        return {
            "recId": 0,
            "status": f"Task failed: {str(e)}",
            "sent_at": None,
            "to": sms_data.get("to", ""),
            "text": sms_data.get("text", ""),
            "from_number": sms_data.get("from_number", "")
        }






@celery_app.task(bind=True, name="app.core.tasks.cleanup_logs_task")
def cleanup_logs_task(self):
    """
    Periodic task to cleanup old logs
    """
    try:
        cleanup_all_logs()
        logger.info("Log cleanup task completed successfully", task_id=self.request.id)
        return {"status": "success", "message": "Logs cleaned up successfully"}
    except Exception as e:
        logger.error("Log cleanup task failed",
                    task_id=self.request.id,
                    error=str(e))
        return {"status": "error", "message": f"Failed to cleanup logs: {str(e)}"}
