"""
Database writer thread.

Owns the single SQLite writer connection. Drains three queues (window events,
input buckets, idle events) and batches commits for performance. Using one
dedicated writer thread avoids "database is locked" errors under WAL mode.
"""
from __future__ import annotations

import datetime
import logging
import queue
import threading
import time
from typing import Union

from .config import Config
from .database import Database
from .models import IdleEndEvent, IdleStartEvent, InputBucket, WindowChangeEvent

logger = logging.getLogger(__name__)

_COMMIT_EVERY_N_EVENTS: int = 30
_COMMIT_EVERY_SEC: float = 5.0

Event = Union[WindowChangeEvent, InputBucket, IdleStartEvent, IdleEndEvent]


class DatabaseWriter:
    """
    Single-threaded SQLite writer that drains the event queues produced by
    WindowPoller, InputMonitor, and IdleWatcher.

    Flow:
      _write_loop() → _drain_once() → _handle(event) → Database.*()
    """

    def __init__(
        self,
        database: Database,
        window_queue: queue.Queue[WindowChangeEvent],
        input_queue: queue.Queue[InputBucket],
        idle_queue: queue.Queue[Union[IdleStartEvent, IdleEndEvent]],
        stop_event: threading.Event,
        config: Config,
    ) -> None:
        self._db = database
        self._wq = window_queue
        self._iq = input_queue
        self._idq = idle_queue
        self._stop = stop_event
        self._config = config

        self._current_session_id: int | None = None
        self._events_since_commit = 0
        self._last_commit = time.time()

        self._thread = threading.Thread(
            target=self._write_loop, daemon=True, name="DatabaseWriter"
        )

    def start(self) -> None:
        self._db.connect_writer()
        self._thread.start()

    def _write_loop(self) -> None:
        while not self._stop.is_set():
            self._drain_once()
            time.sleep(0.1)   # short poll — keeps CPU near-zero
        # Final drain after stop signal
        self._drain_once(flush_all=True)
        self._db.commit()

    def _drain_once(self, flush_all: bool = False) -> None:
        processed = 0
        for q in (self._wq, self._iq, self._idq):
            while True:
                try:
                    item = q.get_nowait()
                    self._handle(item)
                    processed += 1
                except queue.Empty:
                    break

        if processed == 0:
            return

        self._events_since_commit += processed
        now = time.time()
        should_commit = (
            flush_all
            or self._events_since_commit >= _COMMIT_EVERY_N_EVENTS
            or (now - self._last_commit) >= _COMMIT_EVERY_SEC
        )
        if should_commit:
            self._db.commit()
            self._events_since_commit = 0
            self._last_commit = now

    def _handle(self, item: Event) -> None:
        try:
            if isinstance(item, WindowChangeEvent):
                self._handle_window(item)
            elif isinstance(item, InputBucket):
                self._db.insert_input_bucket(item)
            elif isinstance(item, IdleStartEvent):
                self._db.open_idle(item.ts, item.date)
            elif isinstance(item, IdleEndEvent):
                self._db.close_idle(item.ts)
        except Exception:
            logger.exception("DB write error for %s", type(item).__name__)

    def _handle_window(self, event: WindowChangeEvent) -> None:
        now_date = datetime.datetime.fromtimestamp(event.change_ts).strftime(
            "%Y-%m-%d"
        )
        # ── Close the previous session ────────────────────────────────────────
        if self._current_session_id is not None:
            duration = event.change_ts - event.prev_start
            if duration >= self._config.min_session_sec:
                self._db.close_session(self._current_session_id, event.change_ts)
            else:
                # Discard sub-threshold flashes (e.g. tooltips, notifications)
                self._db.delete_session(self._current_session_id)
            self._current_session_id = None

        # ── Open the new session ──────────────────────────────────────────────
        if event.new_exe:
            title = event.new_title
            # Apply title redaction if configured for this exe
            if event.new_exe in self._config.redact_title_exes:
                title = "[redacted]"

            self._current_session_id = self._db.open_session(
                exe=event.new_exe,
                title=title,
                category=event.category,
                ts=event.change_ts,
                date=now_date,
            )
