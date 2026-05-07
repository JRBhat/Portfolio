"""Excel audit logging utilities.

This module persists `AuditEvent` records into an Excel workbook using openpyxl
in append mode (O(1) per event). The logger will create the file if it does not
already exist. Note that Excel does not support timezone-aware datetimes, so
any timezone information is removed before writing.
"""

import pandas as pd
from openpyxl import load_workbook
from pathlib import Path
from models import AuditEvent


class ExcelAuditLogger:
    """Append `AuditEvent` records into an Excel workbook.

    Parameters
    ----------
    excel_path
        Path to the Excel file used for persisting audit records. If the file
        does not exist it will be created automatically with columns taken
        from `AuditEvent`'s model fields.
    """

    def __init__(self, excel_path: Path):
        self.excel_path = excel_path
        if not excel_path.exists():
            self._initialize_file()


    def _initialize_file(self) -> None:
        """Create a new Excel workbook containing the appropriate columns."""
        df = pd.DataFrame(columns=AuditEvent.model_fields.keys())
        df.to_excel(self.excel_path, index=False)


    def log_event(self, event: AuditEvent) -> None:
        """Append a single `AuditEvent` row to the Excel file."""
        event_data = event.model_dump()
        if event_data["timestamp"].tzinfo is not None:
            event_data["timestamp"] = event_data["timestamp"].replace(tzinfo=None)
        wb = load_workbook(self.excel_path)
        ws = wb.active
        ws.append(list(event_data.values()))
        wb.save(self.excel_path)