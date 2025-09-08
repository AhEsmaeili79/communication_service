from fastapi import APIRouter, HTTPException
from app.schemas.email_schema import EmailRequest
from app.services.email.email_service import email_service

router = APIRouter(prefix="/email", tags=["Email"])


@router.post("/send")
def send_email(
    email_request: EmailRequest
):
    """
    Send email synchronously
    """
    try:
        # Send email immediately
        result = email_service.send_email(email_request)

        # Return minimal success response
        return {
            "success": True,
            "to": result.to
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


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

