import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

class IngestionAuditLogger:
    """Handles structured JSONL audit logging for every BrandSignal ingestion run."""

    def __init__(self, logs_dir: str = "data/raw/logs", base_dir: str = "."):
        self.logs_dir = os.path.join(base_dir, logs_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

    def log_run(
        self,
        job_start_time: datetime,
        job_end_time: datetime,
        source_name: str,
        brand_id: Optional[str],
        http_status: Optional[int],
        records_extracted: int,
        records_passed: int,
        records_rejected: int,
        execution_status: str,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates an audit entry, appends to the daily JSONL log file, and returns the dict."""
        log_entry = {
            "log_id": str(uuid.uuid4()),
            "job_start_time": job_start_time.isoformat(),
            "job_end_time": job_end_time.isoformat(),
            "source_name": source_name,
            "brand_id": brand_id,
            "http_status": http_status,
            "records_extracted": records_extracted,
            "records_passed": records_passed,
            "records_rejected": records_rejected,
            "error_message": error_message,
            "execution_status": execution_status
        }

        date_str = job_start_time.strftime("%Y-%m-%d")
        log_file = os.path.join(self.logs_dir, f"ingestion_audit_{date_str}.jsonl")

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

        return log_entry
