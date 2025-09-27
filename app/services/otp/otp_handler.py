import logging
import asyncio
from typing import Dict, Any
from datetime import datetime

from app.services.email.email_service import email_service
from app.services.sms.sms_service import sms_service
from app.schemas.email_schema import EmailRequest
from app.schemas.sms_schema import SMSRequest

logger = logging.getLogger(__name__)


class OTPHandler:
    """Handles OTP message processing for both email and SMS"""
    
    def __init__(self):
        self.email_service = email_service
        self.sms_service = sms_service
    
    def handle_email_otp(self, message_data: Dict[str, Any]) -> bool:
        """
        Handle email OTP message from RabbitMQ
        
        Args:
            message_data: Dictionary containing OTP message data
                - identifier: Email address
                - otp_code: OTP code to send
                - timestamp: Message timestamp
        
        Returns:
            bool: True if processed successfully, False otherwise
        """
        try:
            identifier = message_data.get("identifier")
            otp_code = message_data.get("otp_code")
            timestamp = message_data.get("timestamp")
            
            if not identifier or not otp_code:
                logger.error("Invalid email OTP message: missing identifier or otp_code")
                return False
            
            logger.info(f"Processing email OTP for {identifier}: {otp_code}")

            # Create email request with OTP content
            subject = f"Verification Code: {otp_code}"

            # Create modern, concise HTML email template
            body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #374151;
            max-width: 480px;
            margin: 0 auto;
            background: #f9fafb;
            padding: 20px;
        }}
        .card {{
            background: white;
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        .logo {{
            font-size: 28px;
            margin-bottom: 16px;
        }}
        .title {{
            font-size: 20px;
            font-weight: 600;
            color: #111827;
            margin-bottom: 8px;
        }}
        .subtitle {{
            color: #6b7280;
            margin-bottom: 24px;
        }}
        .otp-code {{
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            color: white;
            font-size: 36px;
            font-weight: 700;
            font-family: 'Monaco', 'Menlo', monospace;
            letter-spacing: 8px;
            padding: 20px 16px;
            border-radius: 12px;
            margin: 24px 0;
            display: inline-block;
            box-shadow: 0 4px 14px 0 rgba(59, 130, 246, 0.3);
        }}
        .timer {{
            background: #fef3c7;
            color: #92400e;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            display: inline-block;
            margin-bottom: 16px;
        }}
        .warning {{
            background: #fef2f2;
            color: #991b1b;
            padding: 16px;
            border-radius: 8px;
            font-size: 14px;
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 32px;
            padding-top: 24px;
            border-top: 1px solid #e5e7eb;
            color: #9ca3af;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">🔐</div>
        <h1 class="title">Verify Your Account</h1>
        <p class="subtitle">Enter this code to complete your verification</p>

        <div class="timer">⏰ Expires in 5 minutes</div>

        <div class="otp-code">{otp_code}</div>

        <div class="warning">
            <strong>Don't share this code</strong> with anyone. Our team will never ask for it.
        </div>

        <div class="footer">
            <p>If you didn't request this code, please ignore this email.</p>
            <p>© 2025 Your Company</p>
        </div>
    </div>
</body>
</html>"""

            email_request = EmailRequest(to=identifier, subject=subject, body=body)

            # Send email with OTP using asyncio.run for sync context
            response = asyncio.run(self._send_otp_email(email_request))
            
            if response:
                logger.info(f"Email OTP sent successfully to {identifier}")
                return True
            else:
                logger.error(f"Failed to send email OTP to {identifier}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing email OTP message: {e}")
            return False
    
    def handle_sms_otp(self, message_data: Dict[str, Any]) -> bool:
        try:
            identifier = message_data.get("identifier")
            otp_code = message_data.get("otp_code")
            timestamp = message_data.get("timestamp")

            if not identifier or not otp_code:
                logger.error("Invalid SMS OTP message: missing identifier or otp_code")
                return False

            logger.info(f"Processing SMS OTP for {identifier}: {otp_code}")

            # Create SMS request with OTP content using original phone number
            # Let the SMS service handle any phone number formatting/validation
            sms_text = f"کد OTP شما: {otp_code}"
            sms_request = SMSRequest(to=identifier, text=sms_text)

            # Send SMS with OTP using asyncio.run for sync context
            try:
                response = asyncio.run(self.sms_service.send_sms(sms_request))

                # Check if SMS was sent successfully
                # "ارسال موفق بود" = successfully sent, "successful" = English success, "200" = HTTP success
                if response and response.status and "موفق" in response.status:
                    logger.info(f"SMS OTP sent successfully to {identifier}")
                    return True
                else:
                    logger.error(f"Failed to send SMS OTP to {identifier}. Status: {response.status if response else 'No response'}")
                    return False

            except Exception as e:
                # SMS service threw an exception (network error, API error, etc.)
                logger.error(f"SMS service error for {identifier}: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Error processing SMS OTP message: {e}")
            return False
    
    async def _send_otp_email(self, email_request: EmailRequest) -> bool:
        """
        Send OTP email with custom content

        Args:
            email_request: Email request object with OTP content

        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            response = await self.email_service.send_email(email_request)

            if response and response.status == "sent":
                logger.info(f"OTP email sent to {email_request.to}")
                return True
            else:
                logger.error(f"Failed to send OTP email to {email_request.to}")
                return False

        except Exception as e:
            logger.error(f"Error sending OTP email: {e}")
            return False


# Global OTP handler instance
otp_handler = OTPHandler()
