"""Filesystem watcher handling and session tracking.

The `DirectoryEventHandler` listens for filesystem changes (create/modify)
and tracks active 'copy' sessions per folder. When sessions are idle longer
than a configured timeout the handler finalises them and logs a
`COPY_COMPLETED` event, optionally referencing the most recent TeraCopy
report.
"""

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from datetime import datetime, timezone
from pathlib import Path
from models import AuditEvent, CopySession
from excel_logger import ExcelAuditLogger
from teracopy_reports import TeraCopyReportFinder


class DirectoryEventHandler(FileSystemEventHandler):
    """Handle filesystem events and manage active copy sessions.

    The handler tracks activity per parent folder. Calls to `finalize_inactive_sessions`
    should be made periodically by an external loop (see `main.py`). When
    finalising, the handler will attempt to find a relevant TeraCopy report
    using the provided `report_finder` object.
    """

    def __init__(self, logger: ExcelAuditLogger):
        self.logger = logger
        self.active_copies: dict[str, CopySession] = {}


    def on_created(self, event: FileSystemEvent) -> None:
        """Called when files or directories are created.

        Directories trigger a `NEW_SUBFOLDER` event; files update the
        corresponding `CopySession` activity timestamp.
        """
        if event.is_directory:
            self._log_folder_creation(event.src_path)
        else:
            self._track_file_activity(event.src_path)


    def on_modified(self, event: FileSystemEvent) -> None:
        """Called when a file is modified; used to extend session activity."""
        if not event.is_directory:
            self._track_file_activity(event.src_path)


    def _log_folder_creation(self, path: str) -> None:
        """Log a `NEW_SUBFOLDER` event for folder creations.

        Timestamps are recorded with microseconds stripped to keep the Excel
        output clean and consistent.
        """
        event = AuditEvent(
            timestamp=datetime.now().replace(microsecond=0),
            event_type="NEW_SUBFOLDER",
            path=path,
            details="Subfolder created"
        )
        self.logger.log_event(event)

    def _track_file_activity(self, file_path: str) -> None:
        """Create or update a `CopySession` for the parent directory of `file_path`."""
        parent = str(Path(file_path).parent)
        self.active_copies[parent] = CopySession(
            folder_path=parent,
            last_activity=datetime.now().replace(microsecond=0)
        )


    def finalize_inactive_sessions(self, report_finder: TeraCopyReportFinder) -> None:
        """Finalize sessions that have been inactive longer than `report_finder.timeout`.

        For each finalized session a `COPY_COMPLETED` `AuditEvent` is logged.
        """
        now = datetime.now().replace(microsecond=0)
        for folder, session in list(self.active_copies.items()):
            if (now - session.last_activity).total_seconds() > report_finder.timeout:
                report = report_finder.find_latest_report()
                event = AuditEvent(
                    timestamp=now,
                    event_type="COPY_COMPLETED",
                    path=folder,
                    details=f"TeraCopy report: {report}" if report else "No report found"
                )
                self.logger.log_event(event)
                del self.active_copies[folder] 