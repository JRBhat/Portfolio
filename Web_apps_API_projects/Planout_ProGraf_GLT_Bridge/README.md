# Planout–GLT Bridge

> A Flask web application that reads scheduling data from Planout (Resource Management/ clinical study scheduling tool) MSSQL database, exposes it via a browser interface, and pushes settings to a building HVAC system (GLT) — with email reporting and an override layer.

---

## Project Overview

- **Problem**: Planout (a clinical study scheduling tool) holds room and resource booking data that needs to be synchronised with a building automation GLT controller. This synchronisation previously required manual data export and re-entry.
- **Type**: Integration middleware / REST bridge
- **Approach**: Flask polls an MSSQL database on demand, transforms the scheduling data, applies configurable overrides, sends it to the GLT via JSON, and provides a web interface for inspection and manual triggering. A background email scheduler sends periodic reports and alerts.

---

## Objective

- Automate the transfer of Planout scheduling data to the GLT system.
- Provide a browser-based dashboard for operations staff to inspect current state and manage overrides.
- Send automated email reports on a configurable schedule.

---

## Dataset

| Field | Details |
|---|---|
| Source | MSSQL database (Planout scheduling system) |
| Connection | pyodbc with ODBC Driver 18 for SQL Server; credentials via environment variables |
| Key data | Project names, resource names, room definitions, scheduling time windows |
| Target | GLT system (building automation controller) via JSON push |

---

## Methodology

1. **Data fetch** — `PlanoutImport.fetch()` executes a parameterised SQL query against the configured MSSQL database and returns a list of scheduling records filtered by resource.
2. **Override layer** — `Overrides` applies manual corrections to the fetched data (e.g., room assignments not reflected in Planout).
3. **GLT translation** — `translatePlanoutListToGLTSettingsAndAddOverrides()` maps scheduling records to GLT-compatible JSON.
4. **Push to GLT** — `sendJSON.sendJSON()` POSTs the translated data to the GLT endpoint.
5. **Web interface** — Flask routes expose `planoutview`, `gltview`, `combinedview`, override management forms, and resource output pages.
6. **Email scheduler** — `EmailScheduler` runs as a background thread and sends formatted HTML email reports on a cron-style schedule.

---

## Code Structure

```
Planout_ProGraf_GLT_Bridge_APIFLASK/
├── app_v3_resource_multiple.py                          # Flask app entry point and all routes
├── PlanoutImport_MSSQL_adjusted_V5_multi_resource_filter.py  # MSSQL fetch and GLT translation
├── Overrides.py                                         # Manual override management
├── RoomDefinitions.py                                   # Room name and config mappings
├── sendJSON.py                                          # GLT JSON push client
├── SendEmail.py                                         # SMTP email sender
├── EmailScheduler.py                                    # Background scheduler (APScheduler or threading)
├── email_config.py                                      # Email configuration constants
└── super/                                               # Archived/superseded files (excluded from git)
```

---

## Key Logic

The connection string is built from environment variables (`DB_SERVER`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`) rather than hardcoded values, making the deployment configurable without source changes. Database credentials are never exposed in code.

The override system allows operations staff to inject corrections for rooms or resources that aren't accurately reflected in Planout (e.g., rooms shared across studies or temporarily reassigned). Overrides are applied after the fetch, before the GLT push.

---

## Results

This is an operational integration service.

Key capabilities:
- On-demand fetch and push to GLT via browser or HTTP call
- Combined view showing Planout data alongside GLT settings in one HTML table
- Override management: create, view, and delete overrides via web forms
- Scheduled email reports with configurable job management

---

## Limitations

- The web interface uses inline HTML strings rather than Jinja2 templates — changing layout requires editing Python source.
- Designed for a single MSSQL instance; no multi-tenancy support.
- German-language UI strings in routes (since system is deployed in a German-speaking environment).

---

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.x |
| Web framework | Flask |
| Database | MSSQL via pyodbc (ODBC Driver 18) |
| Email | smtplib + email / SMTP config |
| Scheduling | Background thread scheduler |
| Data format | JSON (GLT push) |
| Logging | Python standard `logging` |

---

## How to Run

```bash
# Set environment variables for the database connection
export DB_SERVER=your_mssql_server
export DB_NAME=scheduling_db
export DB_USERNAME=db_user
export DB_PASSWORD=your_password

# Install dependencies
pip install flask pyodbc

# Run the Flask app
python app_v3_resource_multiple.py
```

The app listens on `SERVER_HOST:SERVER_PORT` (env vars; defaults to `localhost:5555`).

---

## Business / Practical Value

Eliminates manual data re-entry between the clinical study scheduling system and the building automation controller, reducing synchronisation errors and giving operations staff a live web view of the current state at any time.

---

## Author

Jayesh Bhat · [https://www.linkedin.com/in/jayeshbhat/] · [https://github.com/JRBhat]
