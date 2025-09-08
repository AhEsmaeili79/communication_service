from fastapi import APIRouter, HTTPException

from app.schemas.sms_schema import SMSRequest, SMSResponse
from app.services.sms.sms_service import sms_service, SMSServiceError

router = APIRouter(prefix="/sms", tags=["SMS"])


@router.post("/send", response_model=SMSResponse)
async def send_sms(sms_request: SMSRequest):
    """
    Send SMS with optimized performance
    """
    try:
        result = await sms_service.send_sms(sms_request)
        return result
    except SMSServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")


@router.get("/logs")
def get_sms_logs(days: int = None):
    """
    Get SMS logs from CSV
    """
    try:
        logs = sms_service.get_sms_logs(days)
        return {
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve SMS logs: {str(e)}")

