"""
Session manager — orchestrates all tracker threads and owns the process lifecycle.

Responsibilities:
- Start / stop all background threads in the correct order
- Maintain a PID file so `worktime stop` can find the running instance
- Poll for the stop-flag file written by `worktime stop`
- Ensure a clean shutdown (final queue drain, PID file removal)
"""
from __future__ import annotations

import logging
import os
import queue
import threading
import time
from typing import Union

from .categorizer import Categorizer
from .config import Config
from .database import Database
from .db_writer import DatabaseWriter
from .idle_detector import IdleWatcher
from .input_monitor import InputMonitor
from .models import IdleEndEvent, IdleStartEvent, InputBucket, SharedState, WindowChangeEvent
from .window_tracker import WindowPoller

logger = logging.getLogger(__name__)

_QUEUE_MAXSIZE = 500    # per-queue back-pressure limit


class SessionManager:
    """
    Top-level coordinator for all tracking threads.

    Usage::

        manager = SessionManager(Config.load())
        manager.start()
        try:
            manager.join()      # blocks until stop() is called
        except KeyboardInterrupt:
            pass
        finally:
            manager.stop()
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._stop_event = threading.Event()

        # Shared mutable state (last-activity timestamp, idle flag)
        self._shared_state = SharedState()

        # Inter-thread queues
        self._window_q: queue.Queue[WindowChangeEvent] = queue.Queue(
            maxsize=_QUEUE_MAXSIZE
        )
        self._input_q: queue.Queue[InputBucket] = queue.Queue(maxsize=_QUEUE_MAXSIZE)
        self._idle_q: queue.Queue[Union[IdleStartEvent, IdleEndEvent]] = queue.Queue(
            maxsize=200
        )

        # Components
        self._db = Database(config.db_path)
        cat = Categorizer()

        self._poller = WindowPoller(
            self._window_q, self._shared_state, self._stop_event, config, cat
        )
        self._input_mon = InputMonitor(
            self._input_q, self._shared_state, self._stop_event, config
        )
        self._idle_watch = IdleWatcher(
            self._idle_q, self._shared_state, self._stop_event, config
        )
        self._db_writer = DatabaseWriter(
            self._db,
            self._window_q,
            self._input_q,
            self._idle_q,
            self._stop_event,
            config,
        )

    def start(self) -> None:
        """Start all threads and write the PID file."""
        _write_pid(self._config.pid_file)
        # DatabaseWriter must start first so queues have a consumer before
        # producers begin emitting events
        self._db_writer.start()
        self._poller.start()
        self._input_mon.start()
        self._idle_watch.start()
        logger.info("Tracker started (PID %d)", os.getpid())

    def stop(self) -> None:
        """
        Signal all threads to exit and wait for the database to drain.

        Calling stop() is safe even if start() was never called.
        """
        self._stop_event.set()
        self._input_mon.stop()   # cancels timer + does final input flush

        # Give the DB writer up to 3 seconds to drain remaining queued events
        deadline = time.time() + 3.0
        while time.time() < deadline:
            if (
                self._window_q.empty()
                and self._input_q.empty()
                and self._idle_q.empty()
            ):
                break
            time.sleep(0.1)

        self._config.pid_file.unlink(missing_ok=True)
        logger.info("Tracker stopped")

    def join(self) -> None:
        """
        Block the calling thread until a stop is requested.

        Stop can come from:
        - KeyboardInterrupt (Ctrl+C) in the calling thread
        - The stop-flag file written by `worktime stop`
        - stop_event being set directly (e.g. from a signal handler)
        """
        while not self._stop_event.is_set():
            if self._config.stop_flag_file.exists():
                logger.info("Stop-flag file detected — shutting down")
                try:
                    self._config.stop_flag_file.unlink(missing_ok=True)
                except OSError:
                    pass
                break
            time.sleep(1.0)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_pid(pid_file: "Path") -> None:  # noqa: F821 (Path imported at runtime)
    from pathlib import Path
    Path(pid_file).write_text(str(os.getpid()), encoding="utf-8")


def read_pid(pid_file: "Path") -> int | None:  # noqa: F821
    """Return the PID from the PID file, or None if it does not exist."""
    from pathlib import Path
    try:
        return int(Path(pid_file).read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None
