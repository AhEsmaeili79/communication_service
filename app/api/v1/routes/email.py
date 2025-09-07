from fastapi import APIRouter, HTTPException
from app.schemas.email_schema import EmailRequest
from app.services.email.email_service import email_service
from app.core.tasks import send_email_task
from typing import Dict
import uuid
from datetime import datetime

router = APIRouter(prefix="/email", tags=["Email"])


@router.post("/send")
def send_email(
    email_request: EmailRequest
):
    """
    Send email asynchronously - returns immediately with task ID
    """
    try:
        # Generate a task ID for tracking
        task_id = str(uuid.uuid4())

        # Convert request to dict for Celery task
        email_data = email_request.model_dump()

        # Submit email sending task to Celery
        task = send_email_task.delay(email_data)

        # Return immediate response
        return {
            "task_id": task_id,
            "celery_task_id": task.id,
            "message": "Email sending initiated successfully",
            "status": "queued",
            "to": email_request.to,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue email: {str(e)}")


@router.get("/task/{task_id}")
def get_email_task_status(task_id: str):
    """
    Get the status of an email sending task
    """
    try:
        from app.core.celery_app import celery_app

        # Get the task result from Celery
        task_result = celery_app.AsyncResult(task_id)

        if task_result.state == "PENDING":
            return {
                "task_id": task_id,
                "status": "pending",
                "message": "Email is being processed"
            }
        elif task_result.state == "PROGRESS":
            return {
                "task_id": task_id,
                "status": "in_progress",
                "message": "Email is being sent"
            }
        elif task_result.state == "SUCCESS":
            result = task_result.result
            return {
                "task_id": task_id,
                "status": "completed",
                "message": "Email sent successfully",
                "result": result
            }
        elif task_result.state == "FAILURE":
            return {
                "task_id": task_id,
                "status": "failed",
                "message": f"Email sending failed: {str(task_result.info)}"
            }
        else:
            return {
                "task_id": task_id,
                "status": task_result.state.lower(),
                "message": f"Task is in {task_result.state} state"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.get("/logs")
def get_email_logs(days: int = None):
    """
    Get email logs from CSV
    """
    try:
        logs = email_service.get_email_logs(days)
        return {
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve email logs: {str(e)}")

