"""
Idle detection thread.

Wakes every 10 seconds and compares the current time against the last input
activity timestamp. When the gap exceeds idle_threshold_sec (default: 5 min),
an IdleStartEvent is emitted. When input resumes, an IdleEndEvent is emitted.

Idle start time is backdated to last_activity_ts + threshold so the stored
idle period accurately reflects when idleness began — not when the watcher
first noticed it.
"""
from __future__ import annotations

import datetime
import logging
import queue
import threading
import time

from .config import Config
from .models import IdleEndEvent, IdleStartEvent, SharedState

logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SEC = 10.0


class IdleWatcher:
    """
    Background thread that detects transitions between active and idle states.

    Emits:
    - IdleStartEvent  when elapsed time since last input exceeds the threshold
    - IdleEndEvent    when new input is detected after an idle period
    """

    def __init__(
        self,
        idle_queue: queue.Queue[IdleStartEvent | IdleEndEvent],
        shared_state: SharedState,
        stop_event: threading.Event,
        config: Config,
    ) -> None:
        self._queue = idle_queue
        self._state = shared_state
        self._stop = stop_event
        self._config = config
        self._thread = threading.Thread(
            target=self._watch_loop, daemon=True, name="IdleWatcher"
        )

    def start(self) -> None:
        self._thread.start()

    def _watch_loop(self) -> None:
        while not self._stop.is_set():
            # Sleep for CHECK_INTERVAL_SEC or until stop is signalled
            self._stop.wait(timeout=_CHECK_INTERVAL_SEC)
            if self._stop.is_set():
                break

            now = time.time()
            last_ts = self._state.get_last_activity()
            elapsed = now - last_ts
            currently_idle = elapsed >= self._config.idle_threshold_sec

            if currently_idle and not self._state.is_idle:
                # Transition: active → idle
                self._state.is_idle = True
                # Backdate the idle start to when it actually began
                idle_start_ts = last_ts + self._config.idle_threshold_sec
                event = IdleStartEvent(
                    ts=idle_start_ts,
                    date=datetime.datetime.fromtimestamp(idle_start_ts).strftime(
                        "%Y-%m-%d"
                    ),
                )
                self._put(event)
                logger.debug("Idle started at %s", event.date)

            elif not currently_idle and self._state.is_idle:
                # Transition: idle → active
                self._state.is_idle = False
                self._put(IdleEndEvent(ts=now))
                logger.debug("Idle ended after %.0f s", elapsed)

    def _put(self, event: IdleStartEvent | IdleEndEvent) -> None:
        try:
            self._queue.put(event, block=False)
        except queue.Full:
            logger.warning("Idle queue full — dropping %s", type(event).__name__)
