import os
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from app.core.config import settings


class CSVLogger:
    def __init__(self, log_type: str):
        self.log_type = log_type
        self.logs_dir = settings.logs_directory
        self.retention_days = settings.log_retention_days

        # Ensure logs directory exists
        os.makedirs(self.logs_dir, exist_ok=True)

        if log_type == "sms":
            self.log_file = os.path.join(self.logs_dir, settings.sms_log_file)
            self.columns = ["timestamp", "to", "from_number", "text", "recId", "status", "sent_at"]
        elif log_type == "email":
            self.log_file = os.path.join(self.logs_dir, settings.email_log_file)
            self.columns = ["timestamp", "message_id", "to", "subject", "status", "sent_at"]
        else:
            raise ValueError(f"Invalid log type: {log_type}")

        # Create file if it doesn't exist
        self._ensure_log_file_exists()

    def _ensure_log_file_exists(self):
        """Ensure the log file exists with headers"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(self.columns)
        else:
            # Check if we need to migrate from old format
            self._migrate_old_format_if_needed()

    def _migrate_old_format_if_needed(self):
        """Migrate from old format (with cc/bcc) to new format (without cc/bcc)"""
        if self.log_type != "email":
            return

        try:
            with open(self.log_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                lines = list(reader)

            if not lines:
                return

            # Check if first line has old format with cc/bcc
            header = lines[0]
            if len(header) >= 8 and 'cc' in header and 'bcc' in header:
                print(f"Migrating {self.log_file} from old format to new format...")

                # Create backup
                backup_file = self.log_file + '.backup'
                with open(backup_file, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerows(lines)

                # Write new format
                with open(self.log_file, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(self.columns)  # New headers

                    # Migrate existing data (skip header, only take useful columns)
                    for line in lines[1:]:
                        if len(line) >= 8 and line[0]:  # Old format had 8 columns and skip empty lines
                            # Extract useful data: timestamp, message_id, to, subject, status, sent_at
                            new_line = [line[0], line[1], line[2], line[3], line[6], line[7]]
                            writer.writerow(new_line)

                print(f"Migration completed. Backup saved as {backup_file}")

        except Exception as e:
            print(f"Error migrating log format: {e}")

    def log_sms(self, to: str, from_number: str, text: str, rec_id: Optional[int], status: str):
        """Log SMS sending activity"""
        if self.log_type != "sms":
            raise ValueError("This logger is not configured for SMS logging")

        timestamp = datetime.now().isoformat()
        sent_at = datetime.now().isoformat()

        with open(self.log_file, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, to, from_number, text, rec_id or "", status, sent_at])

    def log_email(self, message_id: str, to: str, subject: str, status: str = "sent"):
        """Log email sending activity"""
        if self.log_type != "email":
            raise ValueError("This logger is not configured for email logging")

        timestamp = datetime.now().isoformat()
        sent_at = datetime.now().isoformat()

        with open(self.log_file, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, message_id, to, subject, status, sent_at])

    def clean_logs_format(self):
        """Manually clean and migrate log format"""
        if self.log_type == "email":
            self._migrate_old_format_if_needed()

    def cleanup_old_logs(self):
        """Remove logs older than retention period"""
        if not os.path.exists(self.log_file):
            return

        try:
            # Read all lines from the CSV file
            with open(self.log_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                lines = list(reader)

            if len(lines) <= 1:  # Only header or empty
                return

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)

            # Keep header and filter recent records
            header = lines[0]
            filtered_lines = [header]

            for line in lines[1:]:
                if len(line) >= 1:
                    try:
                        # Parse timestamp from first column
                        record_timestamp = datetime.fromisoformat(line[0])
                        if record_timestamp >= cutoff_date:
                            filtered_lines.append(line)
                    except (ValueError, IndexError):
                        # Keep malformed lines or lines without timestamp
                        filtered_lines.append(line)

            # Write back filtered records
            with open(self.log_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerows(filtered_lines)

            removed_count = len(lines) - len(filtered_lines)
            if removed_count > 0:
                print(f"Cleaned up {removed_count} old {self.log_type} log entries")

        except Exception as e:
            print(f"Error cleaning up {self.log_type} logs: {e}")

    def get_logs(self, days: int = None) -> List[Dict[str, Any]]:
        """Get logs from the last N days as list of dictionaries"""
        if not os.path.exists(self.log_file):
            return []

        try:
            with open(self.log_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                logs = list(reader)

            if not logs:
                return []

            # Filter by days if specified
            if days:
                cutoff_date = datetime.now() - timedelta(days=days)
                filtered_logs = []

                for log in logs:
                    try:
                        record_timestamp = datetime.fromisoformat(log.get('timestamp', ''))
                        if record_timestamp >= cutoff_date:
                            filtered_logs.append(log)
                    except (ValueError, KeyError):
                        # Keep records with invalid timestamps
                        filtered_logs.append(log)

                return filtered_logs

            return logs

        except Exception as e:
            print(f"Error reading {self.log_type} logs: {e}")
            return []


# Global logger instances
sms_logger = CSVLogger("sms")
email_logger = CSVLogger("email")


def cleanup_all_logs():
    """Cleanup old logs for both SMS and email"""
    sms_logger.cleanup_old_logs()
    email_logger.cleanup_old_logs()


def clean_all_log_formats():
    """Clean and migrate all log formats"""
    email_logger.clean_logs_format()
    sms_logger.clean_logs_format()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean_all_log_formats()
        print("Log format cleaning completed.")
    else:
        # Run cleanup when script is executed directly
        cleanup_all_logs()
