"""Shared data structures used across all tracker modules."""
from __future__ import annotations

import datetime
import threading
import time
from dataclasses import dataclass, field


@dataclass
class SharedState:
    """
    Thread-safe container for last-activity timestamp and idle flag.

    InputMonitor writes to it on every key/mouse event.
    IdleWatcher reads from it to detect idle transitions.
    """

    _last_activity_ts: float = field(default_factory=time.time, repr=False)
    _is_idle: bool = field(default=False, repr=False)
    _lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False
    )

    def record_activity(self) -> None:
        """Update last-activity timestamp to now (called from input callbacks)."""
        with self._lock:
            self._last_activity_ts = time.time()
            self._is_idle = False

    def get_last_activity(self) -> float:
        """Return the last-activity timestamp (safe to call from any thread)."""
        with self._lock:
            return self._last_activity_ts

    @property
    def is_idle(self) -> bool:
        with self._lock:
            return self._is_idle

    @is_idle.setter
    def is_idle(self, value: bool) -> None:
        with self._lock:
            self._is_idle = value


@dataclass
class InputBucket:
    """
    Aggregated input counts for a single time bucket (default: 60 seconds).

    Held in memory by InputMonitor and flushed to the write queue periodically.
    Only counts are stored — no key content is ever captured.
    """

    bucket_ts: float = field(default_factory=time.time)
    date: str = field(default_factory=lambda: datetime.date.today().isoformat())
    key_count: int = 0
    mouse_clicks: int = 0
    mouse_distance: float = 0.0
    _prev_mouse_pos: tuple[int, int] | None = field(default=None, repr=False)

    def reset(self) -> None:
        """Clear counters and start a new bucket at the current time."""
        self.bucket_ts = time.time()
        self.date = datetime.date.today().isoformat()
        self.key_count = 0
        self.mouse_clicks = 0
        self.mouse_distance = 0.0
        self._prev_mouse_pos = None


@dataclass
class WindowChangeEvent:
    """
    Emitted by WindowPoller when the active window changes.

    Both the closing session (prev_*) and the opening session (new_*) are
    bundled together so the DatabaseWriter can close the old row and open the
    new one atomically.
    """

    prev_exe: str | None
    prev_title: str | None
    new_exe: str
    new_title: str
    prev_start: float   # when the previous session started
    change_ts: float    # when the switch happened (= end of prev, start of new)
    category: str = ""  # category of the NEW window (set by WindowPoller)


@dataclass
class IdleStartEvent:
    """Emitted by IdleWatcher when the user transitions to idle."""

    ts: float    # backdated to last_activity_ts + idle_threshold
    date: str


@dataclass
class IdleEndEvent:
    """Emitted by IdleWatcher when the user resumes activity."""

    ts: float    # current time when activity was detected
