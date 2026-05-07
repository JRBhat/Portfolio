"""Domain models used by the directory watcher and logger.

This module defines the data structures recorded to the audit log and the
in-memory session object used to track active copy operations.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from dataclasses import dataclass
class AuditEvent(BaseModel):
    """Pydantic model representing a single audit record.

    Fields
    ------
    timestamp
        UTC timestamp when the event occurred. Prefer timezone-aware
        datetimes; the Excel writer will strip tzinfo when persisting.
    event_type
        Short string categorising the event (for example, 'COPY_COMPLETED').
    path
        Filesystem path related to the event (file or folder).
    details
        Optional free-form details with extra context.
    """
    timestamp: datetime = Field(..., description="UTC timestamp")
    event_type: str
    path: str
    details: str | None = None


@dataclass(frozen=True)
class CopySession:
    """Light-weight record tracking an ongoing copy operation for a folder."""
    folder_path: str
    last_activity: datetime 