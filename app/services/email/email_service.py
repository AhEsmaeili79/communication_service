import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from datetime import datetime

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.schemas.email_schema import EmailRequest, EmailApiResponse, EmailResponse
from app.utils.csv_logger import email_logger
from app.utils.validators import EmailValidator

# Configure logging (fallback to standard logging if structlog not available)
try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Custom exception for Email service errors"""
    pass


class CircuitBreaker:
    """Simplified circuit breaker implementation for email service"""

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


class EmailService:
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.gmail_username = settings.gmail_username
        self.gmail_app_password = settings.gmail_app_password
        self.default_from = settings.gmail_username

        # Rate limiting and circuit breaker
        self.rate_limit_semaphore = asyncio.Semaphore(settings.email_rate_limit)
        self.circuit_breaker = CircuitBreaker(
            settings.email_circuit_breaker_threshold,
            settings.email_circuit_breaker_timeout
        )

    @retry(
        stop=stop_after_attempt(settings.email_retry_attempts),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((smtplib.SMTPException, ConnectionError, TimeoutError))
    )
    def _send_smtp_email_sync(self, email_request: EmailRequest) -> str:
        """Send email via SMTP with retry logic"""
        # Use custom subject/body if provided, otherwise use default welcome message
        if email_request.subject and email_request.body:
            subject = email_request.subject
            body = email_request.body
        else:
            # Default welcome message
            subject = "Welcome to Our Service"
            body = """Hello!

Thank you for your interest in our service. This is an automated message to confirm that our communication system is working properly.

If you have any questions or need assistance, please don't hesitate to contact us.

Best regards,
The Communication Service Team"""

        # Create message
        msg = MIMEMultipart('alternative')  # Use 'alternative' for plain text and HTML
        msg['From'] = self.default_from
        msg['To'] = email_request.to
        msg['Subject'] = subject

        # Check if body contains HTML tags
        is_html = '<html' in body.lower() or '<!doctype html' in body.lower()

        # Add plain text version (always include for compatibility)
        if is_html:
            # Create a plain text version by stripping HTML tags
            import re
            plain_text_body = re.sub(r'<[^>]+>', '', body)
            plain_text_body = re.sub(r'\s+', ' ', plain_text_body).strip()
            msg.attach(MIMEText(plain_text_body, 'plain'))

        # Add HTML version if content is HTML, otherwise use plain text
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))

        # Connect to server and send email
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()  # Enable security
            server.login(self.gmail_username, self.gmail_app_password)
            text = msg.as_string()
            server.sendmail(msg['From'], msg['To'], text)

        return msg.get('Message-ID', 'unknown')

    async def send_email(self, email_request: EmailRequest) -> EmailResponse:
        """
        Send email using SMTP with async support and optimizations
        """
        # Check circuit breaker
        if self.circuit_breaker.is_open():
            error_msg = "Email service is temporarily unavailable due to high failure rate"
            logger.error(f"Circuit breaker open: {error_msg}")
            raise EmailServiceError(error_msg)

        # Apply rate limiting
        async with self.rate_limit_semaphore:
            try:
                # Use custom subject/body if provided, otherwise use default welcome message
                if email_request.subject and email_request.body:
                    subject = email_request.subject
                    body = email_request.body
                else:
                    # Default welcome message
                    subject = "Welcome to Our Service"
                    body = """Hello!

Thank you for your interest in our service. This is an automated message to confirm that our communication system is working properly.

If you have any questions or need assistance, please don't hesitate to contact us.

Best regards,
The Communication Service Team"""

                logger.info(f"Sending email to {email_request.to} with subject {subject}")

                # Run SMTP operation in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                message_id = await loop.run_in_executor(
                    None, 
                    self._send_smtp_email_sync,
                    email_request
                )

                # Create response
                email_response = EmailResponse(
                    to=email_request.to,
                    status="sent"
                )

                # Log success
                email_logger.log_email(
                    to=email_request.to,
                    from_email=self.default_from,
                    subject=subject,
                    message_id=message_id,
                    status="sent"
                )

                # Record success
                self.circuit_breaker.record_success()

                logger.info(f"Email sent successfully with message_id {message_id} to {email_request.to}")

                return email_response

            except Exception as e:
                error_message = f"Email sending failed: {str(e)}"
                logger.error(f"Email sending error: {str(e)}")

                # Handle failure
                self.circuit_breaker.record_failure()

                # Log failure
                email_logger.log_email(
                    to=email_request.to,
                    from_email=self.default_from,
                    subject=subject,
                    message_id=None,
                    status=error_message
                )

                raise EmailServiceError(error_message)

    def get_email_logs(self, days: int = None):
        """
        Get email logs from CSV
        """
        return email_logger.get_logs(days)


# Global email service instance
email_service = EmailService()
