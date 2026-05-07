"""
Input monitoring thread.

Listens for keyboard and mouse events via pynput. Only aggregate counts are
stored — no key content, symbols, or text is ever captured or logged.

Input counts are flushed to the write queue every input_bucket_sec seconds
(default: 60) as InputBucket objects.
"""
from __future__ import annotations

import copy
import logging
import queue
import threading
from typing import Any

from .config import Config
from .models import InputBucket, SharedState

logger = logging.getLogger(__name__)

try:
    from pynput import keyboard, mouse
    _PYNPUT_AVAILABLE = True
except ImportError:
    _PYNPUT_AVAILABLE = False
    logger.warning(
        "pynput not available — input monitoring disabled. "
        "Install with: pixi install"
    )


class InputMonitor:
    """
    Installs global keyboard and mouse listeners and aggregates event counts
    into time-bucketed InputBucket objects.

    Privacy guarantees:
    - _on_key only increments a counter; the key object is never stored.
    - Mouse position is used only to compute cumulative movement distance.
    - No data is written to disk directly; everything goes through the queue.
    """

    def __init__(
        self,
        input_queue: queue.Queue[InputBucket],
        shared_state: SharedState,
        stop_event: threading.Event,
        config: Config,
    ) -> None:
        self._queue = input_queue
        self._state = shared_state
        self._stop = stop_event
        self._config = config

        self._bucket = InputBucket()
        self._lock = threading.Lock()

        self._kb_listener: Any = None
        self._mouse_listener: Any = None
        self._flush_timer: threading.Timer | None = None

    def start(self) -> None:
        if not _PYNPUT_AVAILABLE:
            logger.warning("Skipping input monitoring — pynput not installed")
            return

        self._kb_listener = keyboard.Listener(on_press=self._on_key)
        self._mouse_listener = mouse.Listener(
            on_click=self._on_click,
            on_move=self._on_move,
        )
        self._kb_listener.daemon = True
        self._mouse_listener.daemon = True
        self._kb_listener.start()
        self._mouse_listener.start()
        self._schedule_flush()

    def stop(self) -> None:
        """Cancel the flush timer, do a final flush, and stop listeners."""
        if self._flush_timer:
            self._flush_timer.cancel()
            self._flush_timer = None
        self._flush_bucket()   # persist remaining counts

        if self._kb_listener:
            self._kb_listener.stop()
        if self._mouse_listener:
            self._mouse_listener.stop()

    # ── pynput callbacks (run in listener threads) ────────────────────────────

    def _on_key(self, key: Any) -> None:
        # key is intentionally unused — only the count matters
        with self._lock:
            self._bucket.key_count += 1
        self._state.record_activity()

    def _on_click(self, x: int, y: int, button: Any, pressed: bool) -> None:
        if pressed:
            with self._lock:
                self._bucket.mouse_clicks += 1
            self._state.record_activity()

    def _on_move(self, x: int, y: int) -> None:
        with self._lock:
            prev = self._bucket._prev_mouse_pos
            if prev is not None:
                dx = x - prev[0]
                dy = y - prev[1]
                self._bucket.mouse_distance += (dx * dx + dy * dy) ** 0.5
            self._bucket._prev_mouse_pos = (x, y)
        self._state.record_activity()

    # ── Periodic flush ────────────────────────────────────────────────────────

    def _flush_bucket(self) -> None:
        with self._lock:
            snapshot = copy.copy(self._bucket)
            self._bucket.reset()

        # Only enqueue if there was any activity — avoids empty rows in DB
        if snapshot.key_count > 0 or snapshot.mouse_clicks > 0:
            try:
                self._queue.put(snapshot, block=False)
            except queue.Full:
                logger.warning("Input queue full — dropping bucket")

    def _schedule_flush(self) -> None:
        """Flush and reschedule — forms a self-renewing timer chain."""
        if self._stop.is_set():
            return
        self._flush_bucket()
        self._flush_timer = threading.Timer(
            self._config.input_bucket_sec, self._schedule_flush
        )
        self._flush_timer.daemon = True
        self._flush_timer.start()
