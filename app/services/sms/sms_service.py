import asyncio
import json
import re
import logging
from typing import Dict, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.schemas.sms_schema import SMSRequest, SMSApiResponse, SMSResponse
from app.utils.csv_logger import sms_logger

# Configure logging (fallback to standard logging if structlog not available)
try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class SMSServiceError(Exception):
    """Custom exception for SMS service errors"""
    pass


class SMSService:
    def __init__(self):
        self.api_url = settings.sms_api_url
        self.default_from = settings.sms_from_number
        self.api_key = settings.sms_api_key
        
        # HTTP client configuration for connection pooling
        self.timeout = httpx.Timeout(settings.sms_timeout, connect=settings.http_connect_timeout)
        self.limits = httpx.Limits(
            max_keepalive_connections=settings.http_max_keepalive_connections, 
            max_connections=settings.http_max_connections
        )
        
        # Rate limiting
        self.rate_limit_semaphore = asyncio.Semaphore(settings.sms_rate_limit)
        
        # Circuit breaker state
        self.failure_count = 0
        self.last_failure_time = None
        self.circuit_breaker_threshold = settings.sms_circuit_breaker_threshold
        self.circuit_breaker_timeout = settings.sms_circuit_breaker_timeout

    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.failure_count >= self.circuit_breaker_threshold:
            if self.last_failure_time:
                time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
                if time_since_failure < self.circuit_breaker_timeout:
                    return True
                else:
                    # Reset circuit breaker
                    self.failure_count = 0
                    self.last_failure_time = None
        return False

    def _record_failure(self):
        """Record a failure for circuit breaker"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

    def _record_success(self):
        """Record a success for circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = None

    def _validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format"""
        # Phone number validation - supports international and local formats
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone_number)
        
        # Patterns for different phone number formats
        patterns = [
            r'^\+98[0-9]{10}$',      # +98xxxxxxxxxx (Iran international)
            r'^0098[0-9]{10}$',      # 0098xxxxxxxxxx (Iran international with 00)
            r'^09[0-9]{9}$',         # 09xxxxxxxxx (Iran local)
            r'^5000[0-9]{10}$',     # 5000xxxxxxxxxx (Iran SMS sender)
            r'^\+?[1-9]\d{1,14}$'    # General international format
        ]
        
        return any(re.match(pattern, clean_phone) for pattern in patterns)

    def _sanitize_text(self, text: str) -> str:
        """Sanitize SMS text"""
        # Remove or replace potentially problematic characters
        text = text.strip()
        # Limit length to prevent abuse
        if len(text) > 1600:  # SMS character limit
            text = text[:1600]
        return text

    def _validate_sms_request(self, sms_request: SMSRequest) -> None:
        """Validate SMS request"""
        if not self._validate_phone_number(sms_request.to):
            raise SMSServiceError(f"Invalid phone number format: {sms_request.to}")
        
        if not sms_request.text or not sms_request.text.strip():
            raise SMSServiceError("SMS text cannot be empty")
        
        if len(sms_request.text) > 1600:
            raise SMSServiceError("SMS text exceeds maximum length of 1600 characters")

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
        if self._is_circuit_breaker_open():
            error_msg = "SMS service is temporarily unavailable due to high failure rate"
            logger.error("Circuit breaker open", error=error_msg)
            raise SMSServiceError(error_msg)

        # Validate request
        self._validate_sms_request(sms_request)

        # Sanitize text
        sanitized_text = self._sanitize_text(sms_request.text)

        # Prepare the payload
        payload = {
            "from": sms_request.from_number or self.default_from,
            "to": sms_request.to,
            "text": sanitized_text
        }

        # Apply rate limiting
        async with self.rate_limit_semaphore:
            try:
                logger.info("Sending SMS", to=sms_request.to, from_number=payload["from"])
                
                response = await self._send_http_request(payload)

                if response.status_code == 200:
                    try:
                        api_response = response.json()
                        sms_api_response = SMSApiResponse(**api_response)
                        
                        # Create the response object
                        sms_response = SMSResponse(
                            recId=sms_api_response.recId or 0,
                            status=sms_api_response.status,
                            sent_at=datetime.now(),
                            to=sms_request.to,
                            text=sanitized_text,
                            from_number=payload["from"]
                        )

                        # Log the successful SMS (non-blocking)
                        asyncio.create_task(self._log_sms_async(
                            to=sms_request.to,
                            from_number=payload["from"],
                            text=sanitized_text,
                            rec_id=sms_api_response.recId,
                            status=sms_api_response.status
                        ))

                        # Record success for circuit breaker
                        self._record_success()
                        
                        logger.info("SMS sent successfully", 
                                  rec_id=sms_api_response.recId, 
                                  status=sms_api_response.status)
                        
                        return sms_response

                    except (json.JSONDecodeError, ValueError) as e:
                        error_message = f"Invalid API response format: {str(e)}"
                        logger.error("Invalid API response", error=error_message, response_text=response.text)
                        self._record_failure()
                        raise SMSServiceError(error_message)

                else:
                    error_message = f"API request failed with status {response.status_code}: {response.text}"
                    logger.error("SMS API error", 
                               status_code=response.status_code, 
                               response_text=response.text)
                    self._record_failure()
                    
                    # Log the failed SMS (non-blocking)
                    asyncio.create_task(self._log_sms_async(
                        to=sms_request.to,
                        from_number=payload["from"],
                        text=sanitized_text,
                        rec_id=None,
                        status=error_message
                    ))
                    
                    raise SMSServiceError(error_message)

            except httpx.TimeoutException as e:
                error_message = f"Request timeout: {str(e)}"
                logger.error("SMS request timeout", error=error_message)
                self._record_failure()
                raise SMSServiceError(error_message)
                
            except httpx.ConnectError as e:
                error_message = f"Connection error: {str(e)}"
                logger.error("SMS connection error", error=error_message)
                self._record_failure()
                raise SMSServiceError(error_message)
                
            except httpx.HTTPStatusError as e:
                error_message = f"HTTP error: {str(e)}"
                logger.error("SMS HTTP error", error=error_message)
                self._record_failure()
                raise SMSServiceError(error_message)
                
            except Exception as e:
                error_message = f"Unexpected error: {str(e)}"
                logger.error("SMS unexpected error", error=error_message)
                self._record_failure()
                raise SMSServiceError(error_message)

    async def _log_sms_async(self, to: str, from_number: str, text: str, rec_id: Optional[int], status: str):
        """Async logging to prevent blocking the main flow"""
        try:
            # Run the synchronous logging in a thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                sms_logger.log_sms, 
                to, from_number, text, rec_id, status
            )
        except Exception as e:
            logger.error("Failed to log SMS", error=str(e))


    def get_sms_logs(self, days: int = None):
        """
        Get SMS logs from CSV
        """
        return sms_logger.get_logs(days)



# Global SMS service instance
sms_service = SMSService()