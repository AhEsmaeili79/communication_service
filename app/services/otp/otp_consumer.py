import logging
import threading
from typing import Optional

from app.rabbitmq.consumer import get_rabbitmq_consumer, create_otp_message_callback
from app.rabbitmq.config import rabbitmq_config
from .otp_handler import otp_handler

logger = logging.getLogger(__name__)


class OTPConsumerService:
    """Service to consume OTP messages from RabbitMQ queues"""
    
    def __init__(self):
        self.consumer = get_rabbitmq_consumer()
        self.otp_handler = otp_handler
        self.consumer_thread: Optional[threading.Thread] = None
        self.is_running = False
    
    def start_consuming(self) -> None:
        """Start consuming OTP messages from both email and SMS queues"""
        try:
            logger.info("Starting OTP consumer service...")
            
            # Connect to RabbitMQ
            self.consumer.connect()
            
            # Setup email OTP consumer
            email_callback = create_otp_message_callback(self.otp_handler.handle_email_otp)
            self.consumer.setup_consumer(rabbitmq_config.email_queue, email_callback)
            logger.info(f"Email OTP consumer setup for queue: {rabbitmq_config.email_queue}")
            
            # Setup SMS OTP consumer
            sms_callback = create_otp_message_callback(self.otp_handler.handle_sms_otp)
            self.consumer.setup_consumer(rabbitmq_config.sms_queue, sms_callback)
            logger.info(f"SMS OTP consumer setup for queue: {rabbitmq_config.sms_queue}")
            
            # Start consuming in a separate thread
            self.is_running = True
            self.consumer_thread = threading.Thread(target=self._consume_messages, daemon=True)
            self.consumer_thread.start()
            
            logger.info("OTP consumer service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start OTP consumer service: {e}")
            raise
    
    def stop_consuming(self) -> None:
        """Stop consuming OTP messages"""
        try:
            logger.info("Stopping OTP consumer service...")
            self.is_running = False
            
            if self.consumer:
                self.consumer.stop_consuming()
                self.consumer.disconnect()
            
            if self.consumer_thread and self.consumer_thread.is_alive():
                self.consumer_thread.join(timeout=5)
            
            logger.info("OTP consumer service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping OTP consumer service: {e}")
    
    def _consume_messages(self) -> None:
        """Internal method to consume messages (runs in separate thread)"""
        try:
            while self.is_running:
                self.consumer.start_consuming()
        except Exception as e:
            logger.error(f"Error in consumer thread: {e}")
            self.is_running = False
    
    def is_healthy(self) -> bool:
        """Check if the consumer service is healthy"""
        return self.is_running and self.consumer_thread and self.consumer_thread.is_alive()


# Global OTP consumer service instance
otp_consumer_service = OTPConsumerService()
