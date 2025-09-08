import os
import csv
import asyncio
import aiofiles
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque
import threading
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings


class AsyncCSVLogger:
    def __init__(self, log_type: str):
        self.log_type = log_type
        self.logs_dir = settings.logs_directory
        self.retention_days = settings.log_retention_days

        # Ensure logs directory exists
        os.makedirs(self.logs_dir, exist_ok=True)

        if log_type == "sms":
            self.log_file = os.path.join(self.logs_dir, settings.sms_log_file)
            self.columns = ["timestamp", "to", "from_number", "text", "recId", "status", "sent_at"]
        else:
            raise ValueError(f"Invalid log type: {log_type}")

        # Create file if it doesn't exist
        self._ensure_log_file_exists()

        # Buffer for batch writing
        self.buffer = deque()
        self.buffer_lock = threading.Lock()
        self.buffer_size = 100  # Write to disk when buffer reaches this size
        self.flush_interval = 30  # Flush buffer every 30 seconds
        
        # Thread pool for file operations
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="csv_logger")
        
        # Start background flush task
        self._start_background_flush()

    def _ensure_log_file_exists(self):
        """Ensure the log file exists with headers"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(self.columns)

    def _start_background_flush(self):
        """Start background task to flush buffer periodically"""
        def flush_worker():
            while True:
                asyncio.run(self._flush_buffer())
                threading.Event().wait(self.flush_interval)
        
        flush_thread = threading.Thread(target=flush_worker, daemon=True)
        flush_thread.start()

    async def _flush_buffer(self):
        """Flush the buffer to disk"""
        with self.buffer_lock:
            if not self.buffer:
                return
            
            # Get all items from buffer
            items_to_write = list(self.buffer)
            self.buffer.clear()
        
        if items_to_write:
            await self._write_to_file_async(items_to_write)

    async def _write_to_file_async(self, items: List[List[str]]):
        """Write items to file asynchronously"""
        try:
            async with aiofiles.open(self.log_file, 'a', newline='', encoding='utf-8') as file:
                for item in items:
                    await file.write(','.join(f'"{str(field)}"' for field in item) + '\n')
        except Exception as e:
            print(f"Error writing to log file: {e}")

    def log_sms(self, to: str, from_number: str, text: str, rec_id: Optional[int], status: str):
        """Log SMS sending activity (synchronous interface for compatibility)"""
        timestamp = datetime.now().isoformat()
        sent_at = datetime.now().isoformat()
        
        log_entry = [timestamp, to, from_number, text, rec_id or "", status, sent_at]
        
        with self.buffer_lock:
            self.buffer.append(log_entry)
            
            # Flush if buffer is full
            if len(self.buffer) >= self.buffer_size:
                asyncio.create_task(self._flush_buffer())

    async def log_sms_async(self, to: str, from_number: str, text: str, rec_id: Optional[int], status: str):
        """Log SMS sending activity asynchronously"""
        timestamp = datetime.now().isoformat()
        sent_at = datetime.now().isoformat()
        
        log_entry = [timestamp, to, from_number, text, rec_id or "", status, sent_at]
        
        with self.buffer_lock:
            self.buffer.append(log_entry)
            
            # Flush if buffer is full
            if len(self.buffer) >= self.buffer_size:
                await self._flush_buffer()

    async def cleanup_old_logs_async(self):
        """Remove logs older than retention period asynchronously"""
        if not os.path.exists(self.log_file):
            return

        try:
            # Read all lines from the CSV file
            async with aiofiles.open(self.log_file, 'r', encoding='utf-8') as file:
                content = await file.read()
                lines = content.strip().split('\n')

            if len(lines) <= 1:  # Only header or empty
                return

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)

            # Keep header and filter recent records
            header = lines[0]
            filtered_lines = [header]

            for line in lines[1:]:
                if line.strip():
                    try:
                        # Parse timestamp from first column
                        fields = line.split(',')
                        if fields and fields[0].strip('"'):
                            record_timestamp = datetime.fromisoformat(fields[0].strip('"'))
                            if record_timestamp >= cutoff_date:
                                filtered_lines.append(line)
                    except (ValueError, IndexError):
                        # Keep malformed lines or lines without timestamp
                        filtered_lines.append(line)

            # Write back filtered records
            async with aiofiles.open(self.log_file, 'w', encoding='utf-8') as file:
                await file.write('\n'.join(filtered_lines))

            removed_count = len(lines) - len(filtered_lines)
            if removed_count > 0:
                print(f"Cleaned up {removed_count} old {self.log_type} log entries")

        except Exception as e:
            print(f"Error cleaning up {self.log_type} logs: {e}")

    def cleanup_old_logs(self):
        """Remove logs older than retention period (synchronous interface)"""
        asyncio.run(self.cleanup_old_logs_async())

    async def get_logs_async(self, days: int = None) -> List[Dict[str, Any]]:
        """Get logs from the last N days as list of dictionaries asynchronously"""
        if not os.path.exists(self.log_file):
            return []

        try:
            async with aiofiles.open(self.log_file, 'r', encoding='utf-8') as file:
                content = await file.read()
                lines = content.strip().split('\n')

            if not lines or len(lines) <= 1:
                return []

            # Parse CSV
            reader = csv.DictReader(lines)
            logs = list(reader)

            if not logs:
                return []

            # Filter by days if specified
            if days:
                cutoff_date = datetime.now() - timedelta(days=days)
                filtered_logs = []

                for log in logs:
                    try:
                        record_timestamp = datetime.fromisoformat(log.get('timestamp', '').strip('"'))
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

    def get_logs(self, days: int = None) -> List[Dict[str, Any]]:
        """Get logs from the last N days as list of dictionaries (synchronous interface)"""
        return asyncio.run(self.get_logs_async(days))

    async def flush(self):
        """Manually flush the buffer"""
        await self._flush_buffer()

    def __del__(self):
        """Cleanup on destruction"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)


# Global logger instances
sms_logger = AsyncCSVLogger("sms")


def cleanup_all_logs():
    """Cleanup old logs for SMS (synchronous interface)"""
    sms_logger.cleanup_old_logs()


async def cleanup_all_logs_async():
    """Cleanup old logs for SMS (asynchronous interface)"""
    await sms_logger.cleanup_old_logs_async()


def clean_all_log_formats():
    """Clean and migrate all log formats"""
    # This function can be extended for log format migrations
    pass


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean_all_log_formats()
        print("Log format cleaning completed.")
    else:
        # Run cleanup when script is executed directly
        cleanup_all_logs()