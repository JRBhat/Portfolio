"""
Test suite for tracker.session_manager.SessionManager

Integration tests covering the full tracking lifecycle: startup, data
collection, graceful shutdown, PID file management, and stop-flag handling.

These tests start real background threads with fast config timeouts.
All tests are documented but not yet implemented.
Run with: pytest tests/test_session_manager.py -v
"""
import pytest

# conftest.py provides: temp_config


# ── PID file lifecycle ────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_start_creates_pid_file(temp_config):
    """
    After SessionManager.start(), temp_config.pid_file must exist and contain
    the current process PID as a valid integer.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_stop_removes_pid_file(temp_config):
    """
    After SessionManager.stop(), temp_config.pid_file must no longer exist.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_start_fails_if_pid_file_already_exists(temp_config):
    """
    If a PID file already exists when start() is called, the manager must
    not overwrite it (a second instance check). This prevents two trackers
    running simultaneously.

    Note: This guard is currently in main.py (cmd_start); test that the
    read_pid() helper correctly reads the existing PID.
    """
    pass


# ── Stop-flag file mechanism ──────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_join_returns_when_stop_flag_file_created(temp_config, tmp_path):
    """
    When temp_config.stop_flag_file is created while join() is blocking,
    join() must return within ~2 seconds.

    Spawn a thread that writes the stop-flag after 0.5 s, then call join()
    in the main thread and assert it completes before a 5 s timeout.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_join_deletes_stop_flag_file_on_exit(temp_config):
    """
    After join() detects the stop-flag and returns, the stop-flag file must
    have been deleted (so a fresh start does not immediately stop again).
    """
    pass


# ── Thread lifecycle ──────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_all_threads_running_after_start(temp_config):
    """
    After start(), all four daemon threads must be alive:
    WindowPoller, InputMonitor, IdleWatcher, DatabaseWriter.

    Check by name: [t.name for t in threading.enumerate()]
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_stop_terminates_all_threads(temp_config):
    """
    After stop(), all four daemon threads should no longer be alive
    (or at least should not be blocking) within a 5-second timeout.
    """
    pass


# ── Data written to database ──────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_window_session_written_to_db_after_stop(temp_config):
    """
    Start the manager, wait 2 seconds (one poll cycle), then stop.
    The database must contain at least one row in window_sessions.

    Note: Win32 must be available for this test; skip on non-Windows CI.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_input_bucket_written_to_db_after_flush(temp_config):
    """
    With input_bucket_sec=2, after starting the manager and waiting 3 s
    (with simulated key presses via _on_key callback), the database must
    contain at least one row in input_events.
    """
    pass


# ── Stop is idempotent ────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_double_stop_does_not_raise(temp_config):
    """
    Calling stop() twice must not raise any exception (idempotency).
    """
    pass


# ── read_pid helper ───────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Not yet implemented")
def test_read_pid_returns_none_when_file_missing(temp_config):
    """
    read_pid(path) on a non-existent file must return None, not raise.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_read_pid_returns_integer_from_file(temp_config, tmp_path):
    """
    Write "12345\n" to a file. read_pid() must return the integer 12345.
    """
    pass


@pytest.mark.skip(reason="Not yet implemented")
def test_read_pid_returns_none_for_corrupt_file(temp_config, tmp_path):
    """
    Write "not-a-pid" to the PID file. read_pid() must return None gracefully.
    """
    pass
