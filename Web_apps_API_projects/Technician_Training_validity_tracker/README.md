# Technician Training Validity Tracker

> A FastAPI + SQLite web application that tracks training dates for technicians on specific devices and automatically flags expired or soon-to-expire certifications.

---

## Project Overview

- **Problem**: Lab teams operating multiple medical or analytical devices need to ensure every technician is currently trained on each device they operate. Tracking this manually in spreadsheets leads to outdated records and compliance risk.
- **Type**: Web application / CRUD API with minimal UI
- **Approach**: FastAPI serves a lightweight HTML interface backed by a SQLite database. Training records are stored with a calculated `valid_until` date; the UI surfaces upcoming expirations directly.

---

## Objective

- Provide a simple browser-accessible dashboard to record and review technician training validity dates.
- Automatically compute training expiry based on per-device validity periods.

---

## Dataset

| Field | Details |
|---|---|
| Storage | SQLite (`training_tracker.db` — created automatically) |
| Tables | `devices`, `technicians`, `trainings` |
| Key columns | `training_date`, `valid_until` (computed as `training_date + validity_days`) |
| Target | Not applicable — operational tracking, not ML |

---

## Methodology

1. **Data model** — Three SQLAlchemy ORM tables: `Device` (name, validity_days), `Technician` (name), `Training` (technician_id, device_id, training_date, valid_until).
2. **Validity calculation** — `valid_until = training_date + timedelta(days=device.validity_days)` computed at record creation.
3. **CRUD endpoints** — FastAPI routes handle device and technician registration, training record creation, and dashboard display.
4. **HTML responses** — Inline HTML (no template engine) with minimal CSS for quick deployment.
5. **Admin protection** — Write operations require an admin password checked against the `ADMIN_PASSWORD` environment variable (defaults to `"admin123"` — override in production).

---

## Code Structure

```
Technician_Training_validity_tracker/
└── tech_training_env/
    ├── app.py      # Base version with core CRUD endpoints
    └── app_v2.py   # Enhanced version — additional routes and UI improvements
```

---

## Key Logic

The training validity window is entirely driven by `Device.validity_days` — changing this value for a device automatically affects all future training records for that device without code changes. Historical records retain their original `valid_until` date.

The `declarative_base` import was updated from the deprecated `sqlalchemy.ext.declarative` to `sqlalchemy.orm` (required for SQLAlchemy 2.x compatibility).

---

## Results

> No benchmark metrics — this is an operational web application.

Key capabilities:
- Register devices with configurable training validity periods
- Record training events with automatic expiry date calculation
- Dashboard view showing current training status per technician/device pair
- Admin password protection for write operations (env var configurable)

---

## Limitations

- Admin authentication uses a simple password check (not JWT/session-based). Suitable for internal use only; add proper authentication before exposing externally.
- SQLite is the storage backend — not suitable for high-concurrency production deployments; migrate to PostgreSQL for multi-user environments.
- Two version files (`app.py` and `app_v2.py`) exist; `app_v2.py` is the enhanced version. Consolidation into a single `app.py` was planned but left optional.
- Inline HTML templates mean UI changes require editing Python source.

---

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.10+ |
| Web framework | FastAPI |
| Database ORM | SQLAlchemy 2.x (SQLite) |
| Server | Uvicorn |
| Responses | HTMLResponse (inline HTML) |
| Auth | Environment variable password check |

---

## How to Run

```bash
# Install dependencies
pip install fastapi sqlalchemy uvicorn

# Run the enhanced version
uvicorn tech_training_env.app_v2:app --reload

# Open in browser
# http://127.0.0.1:8000
```

Set `ADMIN_PASSWORD` environment variable to override the default before running in any shared environment.

---

## Business / Practical Value

Replaces manual spreadsheet tracking of device training validity with a live web dashboard that automatically shows who needs to be retrained and by when — directly reducing compliance risk in regulated lab environments.

---

## Author

Jayesh Bhat · [LinkedIn] · [GitHub]
