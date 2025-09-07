import smtplib
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
from app.core.config import settings
from app.schemas.email_schema import EmailRequest, EmailResponse
from app.utils.csv_logger import email_logger


class EmailService:
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.username = settings.gmail_username
        self.app_password = settings.gmail_app_password

        # Static email content
        self.static_subject = "Welcome to Our Service"
        self.static_body = """
        Hello!

        Welcome to our service. We're excited to have you on board.

        If you have any questions, please don't hesitate to contact our support team.

        Best regards,
        Our Service Team
        """

    def send_email(self, email_request: EmailRequest) -> EmailResponse:
        """
        Send email using Gmail SMTP with static content
        """
        if not self.username or not self.app_password:
            raise Exception("Gmail credentials not configured. Please set GMAIL_USERNAME and GMAIL_APP_PASSWORD in environment variables or config.")

        # Generate a unique message ID
        message_id = str(uuid.uuid4())

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = email_request.to
            msg['Subject'] = self.static_subject
            msg['Message-ID'] = f"<{message_id}@{self.smtp_server}>"

            # Add static body
            msg.attach(MIMEText(self.static_body, 'plain'))

            # Create SMTP connection
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()

            # Login
            server.login(self.username, self.app_password)

            # Send email to recipient only
            recipients = [email_request.to]
            text = msg.as_string()
            server.sendmail(self.username, recipients, text)
            server.quit()

            # Create response
            email_response = EmailResponse(
                message_id=message_id,
                status="sent",
                sent_at=datetime.now(),
                to=email_request.to,
                subject=self.static_subject
            )

            # Log the successful email
            email_logger.log_email(
                message_id=message_id,
                to=email_request.to,
                subject=self.static_subject,
                status="sent"
            )

            return email_response

        except smtplib.SMTPAuthenticationError as e:
            error_message = f"SMTP Authentication failed: {str(e)}"

            # Log the failed email
            email_logger.log_email(
                message_id=message_id,
                to=email_request.to,
                subject=self.static_subject,
                status=error_message
            )

            raise Exception(error_message)

        except smtplib.SMTPException as e:
            error_message = f"SMTP error: {str(e)}"

            # Log the failed email
            email_logger.log_email(
                message_id=message_id,
                to=email_request.to,
                subject=self.static_subject,
                status=error_message
            )

            raise Exception(error_message)

        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"

            # Log the failed email
            email_logger.log_email(
                message_id=message_id,
                to=email_request.to,
                subject=self.static_subject,
                status=error_message
            )

            raise Exception(error_message)

    def send_bulk_emails(self, email_requests: List[EmailRequest]) -> List[EmailResponse]:
        """
        Send multiple emails
        """
        results = []

        for email_request in email_requests:
            try:
                result = self.send_email(email_request)
                results.append(result)
            except Exception as e:
                # Create a failed response
                failed_response = EmailResponse(
                    message_id=str(uuid.uuid4()),
                    status=f"Failed: {str(e)}",
                    sent_at=datetime.now(),
                    to=email_request.to,
                    subject=self.static_subject
                )
                results.append(failed_response)

        return results

    def get_email_logs(self, days: int = None):
        """
        Get email logs from CSV
        """
        return email_logger.get_logs(days)

    def clean_email_logs(self):
        """
        Clean email logs by removing old test entries and keeping only useful data
        """
        try:
            # Get all logs
            all_logs = email_logger.get_logs()

            # Filter to keep only entries with proper email addresses and successful status
            useful_logs = []
            for log in all_logs:
                # Keep entries that are not test emails and have valid status
                if (log.get('to', '').endswith('@gmail.com') or
                    log.get('to', '').endswith('@example.com') == False) and \
                   log.get('status') in ['sent', 'Sent']:
                    useful_logs.append(log)

            # If we have useful logs, recreate the log file
            if useful_logs:
                import csv
                import os
                from app.core.config import settings

                log_file = os.path.join(settings.logs_directory, settings.email_log_file)

                # Write clean data
                with open(log_file, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(['timestamp', 'message_id', 'to', 'subject', 'status', 'sent_at'])

                    for log in useful_logs:
                        writer.writerow([
                            log.get('timestamp', ''),
                            log.get('message_id', ''),
                            log.get('to', ''),
                            log.get('subject', ''),
                            log.get('status', ''),
                            log.get('sent_at', '')
                        ])

                return f"Cleaned email logs. Kept {len(useful_logs)} useful entries out of {len(all_logs)} total."

            return "No useful logs found to keep."

        except Exception as e:
            return f"Error cleaning logs: {str(e)}"

    def test_connection(self) -> bool:
        """
        Test SMTP connection
        """
        if not self.username or not self.app_password:
            return False

        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.app_password)
            server.quit()
            return True
        except Exception:
            return False


# Global email service instance
email_service = EmailService()
