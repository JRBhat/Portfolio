# WorkTime Observer Logger

> A lightweight desktop activity (productivity)tracker that monitors keyboard/mouse input and active windows, categorises time into work/idle/break buckets, and generates daily summary reports.

---

## Project Overview

- **Problem**: It's hard to know how much of your workday is actually spent working versus idle or switching contexts. Manual time-tracking is tedious and unreliable.
- **Type**: Desktop utility / background service
- **Approach**: Polls active window titles and input device activity at a configurable interval, writes sessions to a local SQLite database, and categorises each session using a rule-based categoriser. Reports are generated on demand via a CLI.

---

## Objective

- Run silently in the background on a developer's machine, recording which applications are in focus and whether the user is actively typing/clicking.
- Produce a concise daily report showing total work time, idle time, and a timestamped activity trail.

---

## Dataset

| Field | Details |
|---|---|
| Source | Local machine (OS window tracking + input device polling) |
| Storage | SQLite database (`activity.db`) |
| Features | Active window title, process name, activity timestamps, idle flag |
| Target | Not applicable — no ML; categorisation is rule-based |

---

## Methodology

1. **Input monitoring** — `input_monitor.py` polls keyboard and mouse events to detect user presence.
2. **Window tracking** — `window_tracker.py` reads the currently active window title and process name.
3. **Session management** — `session_manager.py` groups consecutive activity into sessions and marks boundaries when idle threshold is crossed.
4. **Categorisation** — `categorizer.py` applies rules (e.g., known IDE process names → "work") to label each session.
5. **Persistence** — `db_writer.py` appends session records to SQLite, with a commit-every-N-events optimisation to reduce write frequency.
6. **Reporting** — `reporter.py` queries the database and formats a daily summary with optional time-filtered activity trail.

---

## Code Structure

```
WorkTime_observer_logger/
├── main.py               # CLI entry point (start / stop / report commands)
├── tracker/
│   ├── config.py         # Config dataclass (paths, thresholds, intervals)
│   ├── session_manager.py# Start/stop lifecycle, PID file management
│   ├── input_monitor.py  # Keyboard/mouse activity detection
│   ├── window_tracker.py # Active window title polling
│   ├── categorizer.py    # Rule-based work/idle/break classifier
│   ├── db_writer.py      # SQLite writer with batched commits
│   ├── database.py       # Schema and connection management
│   ├── idle_detector.py  # Idle timeout logic
│   ├── reporter.py       # Daily report generation
│   └── models.py         # Shared state dataclass
└── tests/
    ├── conftest.py        # Fixtures (temp_db, temp_config, shared_state, stop_event)
    ├── test_categorizer.py
    ├── test_database.py
    └── test_session_manager.py
```

---

## Key Logic

The categoriser uses a priority-ordered rule list: process names matching known IDE patterns (e.g., `code.exe`, `pycharm64.exe`, `devenv.exe`) are labelled "work"; browser titles matching news/social patterns are labelled "distraction"; periods with no input events exceeding `idle_threshold_sec` are labelled "idle". Everything else falls through to an "uncategorised" bucket. This keeps the logic auditable without any ML model.

The `db_writer.py` uses two commit triggers — after every `_COMMIT_EVERY_N_EVENTS` events or every `_COMMIT_EVERY_SEC` seconds — to balance durability against I/O overhead.

---

## Results

This is a utility/productivity tool.

Key capabilities:
- Configurable idle threshold and poll interval (set in `Config`)
- Per-day reporting with optional time-bounded activity trail (`--from HH:MM --to HH:MM`)
- Single-instance enforcement via PID file

---

## Limitations

- Windows-specific for active window detection (uses OS APIs via `window_tracker.py`).
- Category rules are hardcoded; customisation requires editing `categorizer.py` directly.
---

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.10+ |
| Storage | SQLite (via standard library `sqlite3`) |
| CLI | argparse |
| Testing | pytest |
| Task runner | pixi |

---

## How to Run

```bash
# Start tracking (runs in foreground; Ctrl+C or 'stop' command to quit)
python main.py start
# or via pixi
pixi run start

# Stop a running instance
python main.py stop

# Print today's report
python main.py report

# Report with time trail for a specific date and time window
python main.py report --date 2026-05-05 --trail --from 09:00 --to 17:00
```

---

## Business / Practical Value

Gives developers and knowledge workers an honest picture of their actual work patterns without any manual logging. The daily report makes it easy to spot patterns like consistently long idle stretches in the afternoon or excessive context-switching between applications.

---

## Author

Jayesh Bhat · [https://www.linkedin.com/in/jayeshbhat/] · [https://github.com/JRBhat]
