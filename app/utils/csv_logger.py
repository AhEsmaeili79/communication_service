import os
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from app.core.config import settings


class SimpleCSVLogger:
    """Simplified CSV logger without complex async/threading overhead"""

    def __init__(self, log_type: str):
        self.log_type = log_type
        self.logs_dir = settings.logs_directory
        self.retention_days = settings.log_retention_days

        os.makedirs(self.logs_dir, exist_ok=True)

        if log_type == "sms":
            self.log_file = os.path.join(self.logs_dir, settings.sms_log_file)
            self.columns = ["timestamp", "to", "from_number", "text", "recId", "status", "sent_at"]
        elif log_type == "email":
            self.log_file = os.path.join(self.logs_dir, settings.email_log_file)
            self.columns = ["timestamp", "to", "from_email", "subject", "message_id", "status", "sent_at"]
        else:
            raise ValueError(f"Invalid log type: {log_type}")

        self._ensure_log_file_exists()

    def _ensure_log_file_exists(self):
        """Ensure the log file exists with headers"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(self.columns)

    def log_sms(self, to: str, from_number: str, text: str, rec_id: Optional[int], status: str):
        """Log SMS sending activity"""
        timestamp = datetime.now().isoformat()
        sent_at = datetime.now().isoformat()

        log_entry = [timestamp, to, from_number, text, rec_id or "", status, sent_at]

        with open(self.log_file, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(log_entry)

    def log_email(self, to: str, from_email: str, subject: str, message_id: Optional[str], status: str):
        """Log email sending activity"""
        timestamp = datetime.now().isoformat()
        sent_at = datetime.now().isoformat()

        log_entry = [timestamp, to, from_email, subject, message_id or "", status, sent_at]

        with open(self.log_file, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(log_entry)

    def cleanup_old_logs(self):
        """Remove logs older than retention period"""
        if not os.path.exists(self.log_file):
            return

        try:
            with open(self.log_file, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            if len(lines) <= 1:  # Only header or empty
                return

            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            header = lines[0]
            filtered_lines = [header]

            for line in lines[1:]:
                if line.strip():
                    try:
                        fields = line.strip().split(',')
                        if fields and fields[0].strip('"'):
                            record_timestamp = datetime.fromisoformat(fields[0].strip('"'))
                            if record_timestamp >= cutoff_date:
                                filtered_lines.append(line.strip())
                    except (ValueError, IndexError):
                        filtered_lines.append(line.strip())

            with open(self.log_file, 'w', encoding='utf-8') as file:
                file.write('\n'.join(filtered_lines) + '\n')

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
            with open(self.log_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                logs = list(reader)

            if not logs:
                return []

            if days:
                cutoff_date = datetime.now() - timedelta(days=days)
                filtered_logs = []

                for log in logs:
                    try:
                        record_timestamp = datetime.fromisoformat(log.get('timestamp', '').strip('"'))
                        if record_timestamp >= cutoff_date:
                            filtered_logs.append(log)
                    except (ValueError, KeyError):
                        filtered_logs.append(log)

                return filtered_logs

            return logs

        except Exception as e:
            print(f"Error reading {self.log_type} logs: {e}")
            return []


# Global logger instances
sms_logger = SimpleCSVLogger("sms")
email_logger = SimpleCSVLogger("email")


def cleanup_all_logs():
    """Cleanup old logs for SMS and Email"""
    sms_logger.cleanup_old_logs()
    email_logger.cleanup_old_logs()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        cleanup_all_logs()
        print("Log cleanup completed.")
    else:
        cleanup_all_logs()