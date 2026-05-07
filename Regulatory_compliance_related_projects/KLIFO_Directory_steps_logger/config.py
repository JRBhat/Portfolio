"""Configuration for the KLIFO Directory Steps Logger.

This module defines application-wide constants used by the monitoring and
logging components. Edit these values to suit your environment. Defaults are
intended for development and testing; for production you may want to override
them via environment-specific configuration or a deployment system.
"""

import os
from pathlib import Path
from typing import Final


# Directory to monitor for filesystem events (files/folders under this
# directory will be observed). Use an absolute Path for clarity.
MONITORED_DIRECTORY: Final[Path] = Path(
    os.environ.get("MONITORED_DIRECTORY", "data/monitored")
)

# Directory where TeraCopy writes its transfer report files. The
# TeraCopy-related logic scans this directory to correlate file transfer
# reports with observed filesystem activity.
TERACOPY_REPORTS_DIRECTORY: Final[Path] = Path(
    os.environ.get("TERACOPY_REPORTS_DIRECTORY", "C:/Users/username/Documents/TeraCopy/Reports")
)

# Path to the Excel workbook used to record audit events. If the file does
# not exist the application will create it on startup.
EXCEL_LOG_PATH: Final[Path] = Path("audit_log.xlsx")

# Number of seconds of inactivity after which an active session is considered
# finished and is eligible for finalization (e.g., writing summary rows).
INACTIVITY_TIMEOUT_SECONDS: Final[int] = 10

# How often (in seconds) the main loop polls for inactive sessions.
POLL_INTERVAL_SECONDS: Final[int] = 1

# Timezone name used when normalising timestamps in logs. Use a named
# timezone such as "UTC" or "Europe/Berlin" depending on your requirements.
TIMEZONE: Final[str] = "UTC"