"""
Test suite for tracker.reporter.Reporter

Tests report generation logic: time aggregation, per-app ranking,
time trail filtering, and graceful handling of missing/empty data.

All tests are documented but not yet implemented.
Run with: pytest tests/test_reporter.py -v
"""
import pytest

# conftest.py provides: temp_config, populated_db


# ── Helper function unit tests ────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_fmt_duration_formats_hours_and_minutes():
    """
    _fmt_duration(3661) → "1h 01m"   (1 hour, 1 minute, 1 second ignored)
    _fmt_duration(600)  → "0h 10m"
    _fmt_duration(0)    → "0h 00m"
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_aggregate_by_app_sums_durations():
    """
    Given three sessions for code.exe (durations 10, 20, 30 sec),
    _aggregate_by_app() must return {"code.exe": (60.0, "work")}.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_aggregate_by_app_skips_open_sessions():
    """
    Sessions where end_ts is None (still open) must not be included in the
    aggregation — their duration is unknown.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_compute_times_sums_active_and_idle():
    """
    Given sessions totalling 3600 s active and idle periods totalling 300 s,
    _compute_times() must return (3600.0, 300.0).
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_parse_hhmm_converts_to_unix_timestamp():
    """
    _parse_hhmm("2026-04-01", "09:30") must return the Unix timestamp for
    2026-04-01 09:30:00 local time.
    """
    pass


# ── generate() integration ────────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_generate_prints_summary_section(temp_config, populated_db, capsys):
    """
    Reporter.generate() must produce output that includes at least the
    strings "Active time" and "Idle time" (the summary panel labels).

    Uses capsys to capture stdout.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_generate_ranks_apps_by_duration(temp_config, populated_db, capsys):
    """
    The app with the highest total duration must appear first in the
    "Top Applications" section.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_generate_no_sessions_prints_warning(temp_config, temp_db, capsys):
    """
    When there are no sessions for the requested date, generate() must print
    a user-friendly message containing "No activity recorded" — not a traceback.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_generate_missing_db_prints_error(temp_config, capsys):
    """
    When the database file does not exist at all, generate() must print an
    error message — not raise FileNotFoundError to the caller.
    """
    pass


# ── Time trail ────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_trail_appears_when_show_trail_true(temp_config, populated_db, capsys):
    """
    generate(show_trail=True) must include the string "Time Trail" in output.
    generate(show_trail=False) must NOT include "Time Trail".
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_trail_from_filter_excludes_earlier_sessions(temp_config, populated_db, capsys):
    """
    generate(show_trail=True, trail_from="12:00") must not display any
    session that started before 12:00 in the time trail section.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_trail_to_filter_excludes_later_sessions(temp_config, populated_db, capsys):
    """
    generate(show_trail=True, trail_to="10:00") must not display any
    session that started after 10:00 in the time trail section.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_trail_idle_rows_are_visually_distinct(temp_config, populated_db, capsys):
    """
    Idle rows in the time trail must include the text "IDLE" (or "─ IDLE ─")
    so users can visually distinguish them from active sessions.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_trail_empty_window_prints_warning(temp_config, populated_db, capsys):
    """
    If the from/to time window contains no events, generate() must print
    a warning rather than an empty table.
    """
    pass


# ── Date argument ─────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_generate_defaults_to_today(temp_config, populated_db, capsys):
    """
    generate(date_str=None) must query for datetime.date.today().isoformat()
    and include today's date in the header.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_generate_accepts_specific_date(temp_config, populated_db, capsys):
    """
    generate(date_str="2026-01-05") must query data for that specific date
    and display "2026-01-05" in the report header.
    """
    pass
