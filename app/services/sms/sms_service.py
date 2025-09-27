import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.schemas.sms_schema import SMSRequest, SMSApiResponse, SMSResponse
from app.utils.csv_logger import sms_logger
from app.utils.validators import PhoneValidator, validate_sms_text

# Configure logging (fallback to standard logging if structlog not available)
try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class SMSServiceError(Exception):
    """Custom exception for SMS service errors"""
    pass


class CircuitBreaker:
    """Simplified circuit breaker implementation"""

    def __init__(self, threshold: int, timeout: int):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None

    def is_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.failure_count >= self.threshold:
            if self.last_failure_time:
                time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
                if time_since_failure < self.timeout:
                    return True
                else:
                    # Reset circuit breaker
                    self.failure_count = 0
                    self.last_failure_time = None
        return False

    def record_failure(self):
        """Record a failure"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

    def record_success(self):
        """Record a success"""
        self.failure_count = 0
        self.last_failure_time = None


class SMSService:
    def __init__(self):
        self.api_url = settings.sms_api_url
        self.default_from = settings.sms_from_number
        self.api_key = settings.sms_api_key

        # HTTP client configuration
        self.timeout = httpx.Timeout(settings.sms_timeout, connect=settings.http_connect_timeout)
        self.limits = httpx.Limits(
            max_keepalive_connections=settings.http_max_keepalive_connections,
            max_connections=settings.http_max_connections
        )

        # Rate limiting and circuit breaker
        self.rate_limit_semaphore = asyncio.Semaphore(settings.sms_rate_limit)
        self.circuit_breaker = CircuitBreaker(
            settings.sms_circuit_breaker_threshold,
            settings.sms_circuit_breaker_timeout
        )

    @retry(
        stop=stop_after_attempt(settings.sms_retry_attempts),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError))
    )
    async def _send_http_request(self, payload: Dict) -> httpx.Response:
        """Send HTTP request with retry logic"""
        async with httpx.AsyncClient(timeout=self.timeout, limits=self.limits) as client:
            response = await client.post(
                self.api_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
                }
            )
            return response

    async def send_sms(self, sms_request: SMSRequest) -> SMSResponse:
        """
        Send SMS using the Melipayamak API with async support and optimizations
        """
        # Check circuit breaker
        if self.circuit_breaker.is_open():
            error_msg = "SMS service is temporarily unavailable due to high failure rate"
            logger.error(f"Circuit breaker open: {error_msg}")
            raise SMSServiceError(error_msg)

        # Convert phone number to Melipayamak format
        converted_phone = PhoneValidator.convert_phone_for_melipayamak(sms_request.to)

        # Prepare payload
        payload = {
            "from": sms_request.from_number or self.default_from,
            "to": converted_phone,
            "text": sms_request.text
        }

        # Apply rate limiting
        async with self.rate_limit_semaphore:
            try:
                logger.info(f"Sending SMS to {converted_phone} (original: {sms_request.to}) from {payload['from']}")

                response = await self._send_http_request(payload)

                if response.status_code == 200:
                    api_response = response.json()
                    sms_api_response = SMSApiResponse(**api_response)

                    # Create response
                    sms_response = SMSResponse(
                        to=sms_request.to,
                        status=sms_api_response.status
                    )

                    # Log success
                    sms_logger.log_sms(
                        to=sms_request.to,
                        from_number=payload["from"],
                        text=sms_request.text,
                        rec_id=sms_api_response.recId,
                        status=sms_api_response.status
                    )

                    # Record success
                    self.circuit_breaker.record_success()

                    logger.info(f"SMS sent successfully with rec_id {sms_api_response.recId} and status {sms_api_response.status}")

                    return sms_response

                else:
                    error_message = f"API request failed: {response.status_code} - {response.text}"
                    logger.error(f"SMS API error with status_code {response.status_code}")

            except Exception as e:
                error_message = f"SMS sending failed: {str(e)}"
                logger.error(f"SMS sending error: {str(e)}")

            # Handle failure
            self.circuit_breaker.record_failure()

            # Log failure
            sms_logger.log_sms(
                to=sms_request.to,
                from_number=payload["from"],
                text=sms_request.text,
                rec_id=None,
                status=error_message
            )

            raise SMSServiceError(error_message)

    def get_sms_logs(self, days: int = None):
        """
        Get SMS logs from CSV
        """
        return sms_logger.get_logs(days)


# Global SMS service instance
sms_service = SMSService()