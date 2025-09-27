import json
import logging
from typing import Callable, Optional
import pika
from .config import rabbitmq_config
from .setup import RabbitMQSetup

logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    """Handles consuming messages from RabbitMQ for Communication Service"""
    
    def __init__(self):
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self.setup = RabbitMQSetup()
    
    def connect(self) -> None:
        """Establish connection to RabbitMQ"""
        try:
            self.connection = self.setup.create_connection()
            self.channel = self.connection.channel()
            
            # Set QoS to process one message at a time
            self.channel.basic_qos(prefetch_count=1)
            
            logger.info("RabbitMQ consumer connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect RabbitMQ consumer: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close RabbitMQ connection"""
        if self.channel and not self.channel.is_closed:
            self.channel.close()
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        logger.info("RabbitMQ consumer disconnected")
    
    def setup_consumer(self, queue_name: str, callback: Callable) -> None:
        """
        Setup consumer for a specific queue
        
        Args:
            queue_name: Name of the queue to consume from
            callback: Function to handle received messages
        """
        if not self.connection or self.connection.is_closed:
            self.connect()
        
        try:
            # Declare queue to ensure it exists (passive=True to check if exists)
            try:
                self.channel.queue_declare(
                    queue=queue_name,
                    passive=True  # Just check if queue exists
                )
            except pika.exceptions.AMQPChannelError:
                # Queue doesn't exist, create it
                self.channel.queue_declare(
                    queue=queue_name,
                    durable=True,
                    exclusive=False,
                    auto_delete=False
                )
            
            # Setup consumer
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=False
            )
            
            logger.info(f"Consumer setup for queue: {queue_name}")
            
        except Exception as e:
            logger.error(f"Failed to setup consumer for queue {queue_name}: {e}")
            raise
    
    def start_consuming(self) -> None:
        """Start consuming messages"""
        try:
            logger.info("Starting to consume messages...")
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            self.stop_consuming()
        except Exception as e:
            logger.error(f"Error while consuming messages: {e}")
            raise
    
    def stop_consuming(self) -> None:
        """Stop consuming messages"""
        if self.channel and not self.channel.is_closed:
            self.channel.stop_consuming()
        logger.info("Stopped consuming messages")


def create_otp_message_callback(handler_func: Callable) -> Callable:
    """
    Create a callback function for processing OTP messages
    
    Args:
        handler_func: Function to handle the OTP message processing
    
    Returns:
        Callback function for RabbitMQ consumer
    """
    def callback(ch, method, properties, body):
        try:
            # Parse message
            message_data = json.loads(body.decode('utf-8'))
            logger.info(f"Received OTP message: {message_data}")

            # Process the message
            success = handler_func(message_data)

            if success:
                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info("OTP message processed successfully")
            else:
                # Reject message without requeueing to prevent infinite loops
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                logger.error("OTP message processing failed, message discarded")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message JSON: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Error processing OTP message: {e}")
            # Don't requeue on unexpected errors to prevent infinite loops
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    return callback


# Global consumer instance
_rabbitmq_consumer: Optional[RabbitMQConsumer] = None


def get_rabbitmq_consumer() -> RabbitMQConsumer:
    """Get or create RabbitMQ consumer instance"""
    global _rabbitmq_consumer
    if _rabbitmq_consumer is None:
        _rabbitmq_consumer = RabbitMQConsumer()
    return _rabbitmq_consumer


def close_rabbitmq_consumer() -> None:
    """Close RabbitMQ consumer connection"""
    global _rabbitmq_consumer
    if _rabbitmq_consumer:
        _rabbitmq_consumer.disconnect()
        _rabbitmq_consumer = None
