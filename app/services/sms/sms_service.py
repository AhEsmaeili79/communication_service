import requests
import json
from typing import Dict, Optional
from datetime import datetime
from app.core.config import settings
from app.schemas.sms_schema import SMSRequest, SMSApiResponse, SMSResponse
from app.utils.csv_logger import sms_logger


class SMSService:
    def __init__(self):
        self.api_url = settings.sms_api_url
        self.default_from = settings.sms_from_number
        self.api_key = settings.sms_api_key

    def send_sms(self, sms_request: SMSRequest) -> SMSResponse:
        """
        Send SMS using the Melipayamak API
        """
        # Prepare the payload
        payload = {
            "from": sms_request.from_number or self.default_from,
            "to": sms_request.to,
            "text": sms_request.text
        }

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=30.0
            )

            if response.status_code == 200:
                api_response = response.json()

                # Validate the API response
                sms_api_response = SMSApiResponse(**api_response)

                # Create the response object
                sms_response = SMSResponse(
                    recId=sms_api_response.recId or 0,
                    status=sms_api_response.status,
                    sent_at=datetime.now(),
                    to=sms_request.to,
                    text=sms_request.text,
                    from_number=payload["from"]
                )

                # Log the successful SMS
                sms_logger.log_sms(
                    to=sms_request.to,
                    from_number=payload["from"],
                    text=sms_request.text,
                    rec_id=sms_api_response.recId,
                    status=sms_api_response.status
                )

                return sms_response

            else:
                error_message = f"API request failed with status {response.status_code}: {response.text}"

                # Log the failed SMS
                sms_logger.log_sms(
                    to=sms_request.to,
                    from_number=payload["from"],
                    text=sms_request.text,
                    rec_id=None,
                    status=error_message
                )

                raise Exception(error_message)

        except requests.RequestException as e:
            error_message = f"Request error: {str(e)}"

            # Log the failed SMS
            sms_logger.log_sms(
                to=sms_request.to,
                from_number=payload["from"],
                text=sms_request.text,
                rec_id=None,
                status=error_message
            )

            raise Exception(error_message)

        except json.JSONDecodeError as e:
            error_message = f"Invalid JSON response: {str(e)}"

            # Log the failed SMS
            sms_logger.log_sms(
                to=sms_request.to,
                from_number=payload["from"],
                text=sms_request.text,
                rec_id=None,
                status=error_message
            )

            raise Exception(error_message)

    def send_bulk_sms(self, sms_requests: list[SMSRequest]) -> list[SMSResponse]:
        """
        Send multiple SMS messages
        """
        results = []

        for sms_request in sms_requests:
            try:
                result = self.send_sms(sms_request)
                results.append(result)
            except Exception as e:
                # Create a failed response
                failed_response = SMSResponse(
                    recId=None,
                    status=f"Failed: {str(e)}",
                    sent_at=datetime.now(),
                    to=sms_request.to,
                    text=sms_request.text,
                    from_number=sms_request.from_number or self.default_from
                )
                results.append(failed_response)

        return results

    def get_sms_logs(self, days: int = None):
        """
        Get SMS logs from CSV
        """
        return sms_logger.get_logs(days)


# Global SMS service instance
sms_service = SMSService()
