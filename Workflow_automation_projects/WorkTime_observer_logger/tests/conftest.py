"""
Pytest fixtures shared across the test suite.
"""
import threading
import time

import pytest

from tracker.config import Config
from tracker.database import Database
from tracker.models import SharedState


@pytest.fixture
def temp_db(tmp_path):
    """
    Provides a temporary SQLite Database instance backed by a fresh file
    in pytest's tmp_path directory.

    Returns a connected Database writer instance ready for use.

    Used by: test_database.py, test_db_writer.py, test_reporter.py,
             test_session_manager.py
    """
    db = Database(tmp_path / "test.db")
    db.connect_writer()
    yield db
    db._writer_conn.close()


@pytest.fixture
def temp_config(tmp_path):
    """
    Provides a Config instance with all paths under pytest's tmp_path.

    Used by: test_session_manager.py, test_idle_detector.py,
             test_input_monitor.py, test_window_tracker.py
    """
    yield Config(
        db_path=tmp_path / "activity.db",
        pid_file=tmp_path / "tracker.pid",
        stop_flag_file=tmp_path / "tracker.stop",
        idle_threshold_sec=2,
        poll_interval_sec=0.1,
        input_bucket_sec=2,
        min_session_sec=0.1,
    )


@pytest.fixture
def populated_db(temp_db):
    """
    A Database instance pre-populated with one week of synthetic activity data.

    Inserts:
      - 50 window sessions spanning 5 weekdays (work, leisure, system mix)
      - Corresponding input_events buckets
      - Several idle_periods per day

    Used by: test_reporter.py, test_database.py (query tests)
    """
    raise NotImplementedError(
        "Implement: insert deterministic synthetic rows into temp_db "
        "and return it."
    )


@pytest.fixture
def shared_state():
    """
    Provides a fresh SharedState instance with last_activity_ts = now.

    Used by: test_idle_detector.py, test_input_monitor.py,
             test_window_tracker.py
    """
    yield SharedState()


@pytest.fixture
def stop_event():
    """
    Provides a threading.Event that can be used to signal background threads
    to stop. Automatically set after the test completes.

    Used by: test_idle_detector.py, test_input_monitor.py,
             test_window_tracker.py, test_session_manager.py
    """
    event = threading.Event()
    yield event
    event.set()  # ensure threads stop after test
