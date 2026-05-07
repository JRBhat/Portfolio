"""
Test suite for tracker.database.Database

Tests the SQLite schema creation, all write operations (via the writer
interface), and all read queries (via the reader interface).

All tests are documented but not yet implemented.
Run with: pytest tests/test_database.py -v
"""
import pytest

# conftest.py provides: temp_db, populated_db


# ── Schema & connection ───────────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_schema_creates_all_tables(temp_db):
    """
    After connect_writer(), three tables must exist in the database:
    window_sessions, input_events, idle_periods.

    Query sqlite_master to verify table names.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_schema_creates_indexes(temp_db):
    """
    idx_ws_date, idx_ie_date, idx_ip_date must be present after schema creation.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_wal_mode_is_enabled(temp_db):
    """
    PRAGMA journal_mode should return 'wal' after connect_writer().
    """
    pass


# ── Session write / read ──────────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_open_session_returns_integer_id(temp_db):
    """
    open_session() must return a positive integer (the SQLite lastrowid).
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_open_session_row_has_null_end_ts(temp_db):
    """
    A freshly opened session must have end_ts = NULL in the database.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_close_session_sets_end_ts(temp_db):
    """
    After close_session(id, ts), the row's end_ts must equal ts and not be NULL.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_delete_session_removes_row(temp_db):
    """
    After delete_session(id), the row must no longer exist.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_query_window_sessions_filters_by_date(temp_db):
    """
    Insert sessions on two different dates.
    query_window_sessions("2026-01-01") must return only that day's rows.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_query_window_sessions_ordered_by_start_ts(temp_db):
    """
    Rows returned by query_window_sessions() must be in ascending start_ts order.
    """
    pass


# ── Input bucket write / read ─────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_insert_input_bucket_stores_correct_counts(temp_db):
    """
    After insert_input_bucket(bucket), query the table directly and verify
    key_count, mouse_clicks, mouse_distance match the bucket values.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_query_input_totals_sums_multiple_buckets(temp_db):
    """
    Insert three buckets for the same date.
    query_input_totals() must return the sum of all three.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_query_input_totals_returns_zeros_for_empty_date(temp_db):
    """
    query_input_totals() for a date with no data must return
    {"total_keys": 0, "total_clicks": 0, "total_distance": 0} (not an error).
    """
    pass


# ── Idle period write / read ──────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_open_idle_creates_row_with_null_end_ts(temp_db):
    """
    open_idle() must insert a row where end_ts IS NULL.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_close_idle_sets_end_ts_and_duration(temp_db):
    """
    After open_idle(start) and close_idle(end), the row must have:
      end_ts = end
      duration_sec ≈ end - start  (within floating-point tolerance)
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_close_idle_targets_most_recent_open_period(temp_db):
    """
    When two idle periods are open (edge case), close_idle() must close
    the one with the latest start_ts, leaving the other untouched.
    """
    pass


# ── Time trail query ──────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_query_trail_merges_sessions_and_idles(populated_db):
    """
    query_trail() must return rows with type='active' and type='idle' merged
    and sorted by start_ts ascending.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_query_trail_from_filter_excludes_earlier_events(populated_db):
    """
    query_trail(date, from_ts=T) must not include any event with start_ts < T.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_query_trail_to_filter_excludes_later_events(populated_db):
    """
    query_trail(date, to_ts=T) must not include any event with start_ts > T.
    """
    pass


# ── Error handling ────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_reader_raises_file_not_found_if_db_missing(tmp_path):
    """
    Calling any query_* method when the database file does not exist must
    raise FileNotFoundError with a human-readable message.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_connect_writer_is_idempotent(temp_db):
    """
    Calling connect_writer() a second time must not raise or corrupt data.
    """
    pass
