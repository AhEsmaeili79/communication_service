from fastapi import APIRouter, HTTPException

from app.schemas.email_schema import EmailRequest, EmailResponse
from app.services.email.email_service import email_service, EmailServiceError

router = APIRouter(prefix="/email", tags=["Email"])


@router.post("/send", response_model=EmailResponse)
async def send_email(email_request: EmailRequest):
    """
    Send email with optimized performance
    """
    try:
        result = await email_service.send_email(email_request)
        return result
    except EmailServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
