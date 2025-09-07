from typing import List
from app.core.celery_app import celery_app
from app.services.sms.sms_service import sms_service
from app.services.email.email_service import email_service
from app.schemas.sms_schema import SMSRequest, SMSResponse
from app.schemas.email_schema import EmailRequest, EmailResponse
from app.utils.csv_logger import cleanup_all_logs


@celery_app.task(bind=True, name="app.core.tasks.send_sms_task")
def send_sms_task(self, sms_data: dict) -> dict:
    """
    Async task to send SMS
    """
    try:
        # Convert dict to SMSRequest
        sms_request = SMSRequest(**sms_data)

        # Send SMS synchronously (since we're in async task)
        import asyncio
        result = asyncio.run(sms_service.send_sms(sms_request))

        # Convert to dict for JSON serialization
        return {
            "recId": result.recId,
            "status": result.status,
            "sent_at": result.sent_at.isoformat(),
            "to": result.to,
            "text": result.text,
            "from_number": result.from_number
        }

    except Exception as e:
        # Return error information
        return {
            "recId": 0,
            "status": f"Task failed: {str(e)}",
            "sent_at": None,
            "to": sms_data.get("to", ""),
            "text": sms_data.get("text", ""),
            "from_number": sms_data.get("from_number", "")
        }


@celery_app.task(bind=True, name="app.core.tasks.send_email_task")
def send_email_task(self, email_data: dict) -> dict:
    """
    Async task to send email
    """
    try:
        # Convert dict to EmailRequest
        email_request = EmailRequest(**email_data)

        # Send email synchronously (since we're in async task)
        import asyncio
        result = asyncio.run(email_service.send_email(email_request))

        # Convert to dict for JSON serialization
        return {
            "message_id": result.message_id,
            "status": result.status,
            "sent_at": result.sent_at.isoformat(),
            "to": result.to,
            "subject": result.subject,
            "cc": result.cc,
            "bcc": result.bcc
        }

    except Exception as e:
        # Return error information
        return {
            "message_id": "",
            "status": f"Task failed: {str(e)}",
            "sent_at": None,
            "to": email_data.get("to", ""),
            "subject": email_data.get("subject", ""),
            "cc": email_data.get("cc", []),
            "bcc": email_data.get("bcc", [])
        }


@celery_app.task(bind=True, name="app.core.tasks.send_bulk_sms_task")
def send_bulk_sms_task(self, sms_list: List[dict]) -> List[dict]:
    """
    Async task to send bulk SMS
    """
    try:
        # Convert list of dicts to list of SMSRequest
        sms_requests = [SMSRequest(**sms_data) for sms_data in sms_list]

        # Send bulk SMS
        import asyncio
        results = asyncio.run(sms_service.send_bulk_sms(sms_requests))

        # Convert to list of dicts for JSON serialization
        return [
            {
                "recId": result.recId,
                "status": result.status,
                "sent_at": result.sent_at.isoformat(),
                "to": result.to,
                "text": result.text,
                "from_number": result.from_number
            }
            for result in results
        ]

    except Exception as e:
        # Return error information for all SMS
        return [
            {
                "recId": 0,
                "status": f"Bulk task failed: {str(e)}",
                "sent_at": None,
                "to": sms_data.get("to", ""),
                "text": sms_data.get("text", ""),
                "from_number": sms_data.get("from_number", "")
            }
            for sms_data in sms_list
        ]


@celery_app.task(bind=True, name="app.core.tasks.send_bulk_email_task")
def send_bulk_email_task(self, email_list: List[dict]) -> List[dict]:
    """
    Async task to send bulk emails
    """
    try:
        # Convert list of dicts to list of EmailRequest
        email_requests = [EmailRequest(**email_data) for email_data in email_list]

        # Send bulk emails
        import asyncio
        results = asyncio.run(email_service.send_bulk_emails(email_requests))

        # Convert to list of dicts for JSON serialization
        return [
            {
                "message_id": result.message_id,
                "status": result.status,
                "sent_at": result.sent_at.isoformat(),
                "to": result.to,
                "subject": result.subject,
                "cc": result.cc,
                "bcc": result.bcc
            }
            for result in results
        ]

    except Exception as e:
        # Return error information for all emails
        return [
            {
                "message_id": "",
                "status": f"Bulk task failed: {str(e)}",
                "sent_at": None,
                "to": email_data.get("to", ""),
                "subject": email_data.get("subject", ""),
                "cc": email_data.get("cc", []),
                "bcc": email_data.get("bcc", [])
            }
            for email_data in email_list
        ]


@celery_app.task(bind=True, name="app.core.tasks.cleanup_logs_task")
def cleanup_logs_task(self):
    """
    Periodic task to cleanup old logs
    """
    try:
        cleanup_all_logs()
        return {"status": "success", "message": "Logs cleaned up successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to cleanup logs: {str(e)}"}
