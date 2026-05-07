# KLIFO Directory Steps Logger

Watches a configured directory for file copy/move activity, integrates TeraCopy transfer reports, and appends structured audit events (Audit trail) to an Excel log.

---

## Project Overview

- **Problem**: In workflows involving large batches of file transfers (e.g., clinical data archiving), there's often no automatic audit trail linking filesystem events to the transfer tool's own reports.
- **Type**: Automation / filesystem monitoring service
- **Approach**: Uses `watchdog` to observe a directory in real time. Events are grouped into copy sessions and finalised once inactivity exceeds a configurable timeout. TeraCopy's XML transfer reports are parsed to enrich each session with transfer metadata before the event is written to Excel.

---

## Objective

- Produce a timestamped, structured Excel audit log of all file copy activity in a monitored directory.
- Automatically close inactive sessions and correlate them with TeraCopy reports.

---

## Dataset

| Field | Details |
|---|---|
| Source | Local filesystem (configured monitored directory) |
| Storage | Excel file (`.xlsx` via openpyxl) |
| Features | File paths, event types, timestamps, TeraCopy report metadata |
| Target | Not applicable — event logging, not prediction |

---

## Methodology

1. **Configuration** — All paths and thresholds read from `config.py` (`MONITORED_DIRECTORY`, `EXCEL_LOG_PATH`, `INACTIVITY_TIMEOUT_SECONDS`, `POLL_INTERVAL_SECONDS`).
2. **Filesystem watching** — `watchdog.Observer` schedules `DirectoryEventHandler` recursively on the monitored path.
3. **Session tracking** — `DirectoryEventHandler` (in `watcher.py`) maintains a `dict[str, CopySession]` of active sessions keyed by source path.
4. **Inactivity finalisation** — On each poll, `finalize_inactive_sessions` checks if `(now - session.last_activity).total_seconds() > timeout` and closes stale sessions.
5. **TeraCopy report correlation** — `TeraCopyReportFinder` (in `teracopy_reports.py`) scans the TeraCopy reports directory for matching transfer XMLs and attaches them to finalised sessions.
6. **Excel logging** — `ExcelAuditLogger` appends each finalised session as a row using `openpyxl` in append mode (O(1) per event).

---

## Code Structure

```
KLIFO_Directory_steps_logger_AUTO/
├── main.py              # Entry point: starts observer, runs poll loop
├── config.py            # All configurable constants
├── watcher.py           # DirectoryEventHandler and CopySession logic
├── excel_logger.py      # ExcelAuditLogger — openpyxl-based row writer
├── teracopy_reports.py  # TeraCopyReportFinder — parses TeraCopy XML reports
└── models.py            # AuditEvent dataclass
```

---

## Key Logic

The original implementation read the entire Excel file on every event (O(n²) total cost). The refactored `log_event` method opens the workbook, calls `ws.append(...)`, and saves — making each write O(1) regardless of log size. This matters for long-running monitoring sessions with thousands of events.

The inactivity timeout uses `timedelta.total_seconds()` rather than `.seconds` to correctly handle timeouts longer than 60 seconds (a bug that was present in the original code).

---

## Results

This is an automation/logging utility for achieving regulatory compliance.

Key capabilities:
- Recursive directory monitoring with configurable poll interval
- Session-based event grouping with automatic timeout-based finalisation
- TeraCopy report correlation for enriched audit entries
- Append-only Excel output suitable for long-running processes

---

## Limitations

- TeraCopy integration assumes TeraCopy's default report directory and XML format; other transfer tools are not supported.
- The Excel log grows indefinitely — no rotation or archiving is built in. But can be integrated if needed.
- Designed for Windows (TeraCopy is Windows-only). However, the `watchdog` component itself is cross-platform.

---

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.10+ |
| Filesystem | watchdog |
| Excel I/O | openpyxl |
| Data models | pydantic (AuditEvent via `model_dump`) |
| Typing | Built-in generics (Python 3.9+) |

---

## How to Run

```bash
# 1. Configure paths and timeouts in config.py

# 2. Run
python main.py
```

The logger runs until interrupted with Ctrl+C. The observer is stopped and joined cleanly on exit.

---

## Business / Practical Value

Gives clinical data operations teams a verifiable, timestamped Excel record of every file movement in a study directory — useful for GxP compliance audits and transfer verification without any manual documentation.

---

## Author

Jayesh Bhat · [https://www.linkedin.com/in/jayeshbhat/] · [https://github.com/JRBhat]
