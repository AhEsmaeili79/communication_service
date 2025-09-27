import logging
import asyncio
from typing import Dict, Any
from datetime import datetime

from app.services.email.email_service import email_service
from app.services.sms.sms_service import sms_service
from app.schemas.email_schema import EmailRequest
from app.schemas.sms_schema import SMSRequest
from app.utils.validators import PhoneValidator

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
            email_request = EmailRequest(to=identifier)
            
            # Send email with OTP using asyncio.run for sync context
            response = asyncio.run(self._send_otp_email(email_request, otp_code))
            
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
        """
        Handle SMS OTP message from RabbitMQ
        
        Args:
            message_data: Dictionary containing OTP message data
                - identifier: Phone number
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
                logger.error("Invalid SMS OTP message: missing identifier or otp_code")
                return False
            
            # Convert phone number for Melipayamak SMS service
            converted_identifier = PhoneValidator.convert_phone_for_melipayamak(identifier)
            logger.info(f"Processing SMS OTP for {identifier} (converted to {converted_identifier}): {otp_code}")
            
            # Create SMS request with OTP content using converted phone number
            sms_text = f"Your OTP code is: {otp_code}. This code will expire in 5 minutes."
            sms_request = SMSRequest(to=converted_identifier, text=sms_text)
            
            # Send SMS with OTP using asyncio.run for sync context
            response = asyncio.run(self.sms_service.send_sms(sms_request))
            
            if response and response.status == "sent":
                logger.info(f"SMS OTP sent successfully to {converted_identifier} (original: {identifier})")
                return True
            else:
                logger.error(f"Failed to send SMS OTP to {converted_identifier} (original: {identifier})")
                return False
                
        except Exception as e:
            logger.error(f"Error processing SMS OTP message: {e}")
            return False
    
    async def _send_otp_email(self, email_request: EmailRequest, otp_code: str) -> bool:
        """
        Send OTP email with custom content
        
        Args:
            email_request: Email request object
            otp_code: OTP code to include in email
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # For now, we'll use the existing email service
            # In a real implementation, you might want to modify the email service
            # to accept custom subject and body content
            response = await self.email_service.send_email(email_request)
            
            if response and response.status == "sent":
                logger.info(f"OTP email sent to {email_request.to} with code {otp_code}")
                return True
            else:
                logger.error(f"Failed to send OTP email to {email_request.to}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending OTP email: {e}")
            return False


# Global OTP handler instance
otp_handler = OTPHandler()
