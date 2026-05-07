
"""KLIFO Directory Steps Logger - main entrypoint.

This module starts filesystem monitoring for the directory configured in
`config.MONITORED_DIRECTORY` and logs detected events to an Excel file at
`config.EXCEL_LOG_PATH` via `ExcelAuditLogger`.

It also uses `TeraCopyReportFinder` to locate TeraCopy transfer reports and
`DirectoryEventHandler.finalize_inactive_sessions` to close out sessions that
have been inactive for `INACTIVITY_TIMEOUT_SECONDS`.

Usage:
    python main.py

Configuration values are loaded from `config.py`.
"""

from __future__ import annotations

import logging
import time
from watchdog.observers import Observer
from config import (
    MONITORED_DIRECTORY,
    EXCEL_LOG_PATH,
    TERACOPY_REPORTS_DIRECTORY,
    INACTIVITY_TIMEOUT_SECONDS,
    POLL_INTERVAL_SECONDS,
)
from excel_logger import ExcelAuditLogger
from watcher import DirectoryEventHandler
from teracopy_reports import TeraCopyReportFinder


def main() -> None:
    """Start directory monitoring and process events until interrupted.

    The function configures the observer and event handler, then enters a
    loop that periodically calls `handler.finalize_inactive_sessions` using a
    `TeraCopyReportFinder` to resolve completed transfers. It runs until the
    process receives a KeyboardInterrupt (Ctrl+C), at which point it stops the
    observer and waits for it to finish.
    """
    audit_logger = ExcelAuditLogger(EXCEL_LOG_PATH)
    handler = DirectoryEventHandler(audit_logger)
    observer = Observer()

    logging.info("Starting directory monitoring for %s", MONITORED_DIRECTORY)
    observer.schedule(handler, str(MONITORED_DIRECTORY), recursive=True)
    observer.start()

    report_finder = TeraCopyReportFinder(TERACOPY_REPORTS_DIRECTORY, INACTIVITY_TIMEOUT_SECONDS)

    try:
        while True:
            # Periodically check for sessions that should be finalized due to inactivity
            handler.finalize_inactive_sessions(report_finder)
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logging.info("Received KeyboardInterrupt; stopping observer...")
    finally:
        observer.stop()
        observer.join()
        logging.info("Observer stopped and joined. Exiting.")


if __name__ == "__main__":
    # Basic logging configuration for the command-line run
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    main()