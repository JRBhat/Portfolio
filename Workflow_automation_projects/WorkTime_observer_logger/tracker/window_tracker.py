"""
Active-window polling thread.

Polls the Windows foreground window every poll_interval_sec seconds using
win32gui/win32process. Emits a WindowChangeEvent to the write queue whenever
the focused application or window title changes.
"""
from __future__ import annotations

import logging
import os
import queue
import threading
import time

from .categorizer import Categorizer
from .config import Config
from .models import SharedState, WindowChangeEvent

logger = logging.getLogger(__name__)

# ── Win32 imports (Windows-only) ──────────────────────────────────────────────
try:
    import win32api
    import win32con
    import win32gui
    import win32process
    import pywintypes
    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False
    logger.warning(
        "pywin32 not available — window tracking disabled. "
        "Install with: pixi install"
    )


def get_active_window() -> tuple[str, str]:
    """
    Return (exe_name, window_title) for the currently focused window.

    Falls back gracefully when:
    - No window is focused       → ("desktop", "")
    - Window belongs to elevated process → ("elevated_process", title)
    - win32 not available        → ("unknown", "")
    """
    if not _WIN32_AVAILABLE:
        return "unknown", ""

    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return "desktop", ""

    title = win32gui.GetWindowText(hwnd)

    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        try:
            exe_path = win32process.GetModuleFileNameEx(handle, 0)
        finally:
            win32api.CloseHandle(handle)
        exe_name = os.path.basename(exe_path).lower()
    except pywintypes.error:
        # UAC-elevated process: we can detect it but not read its exe path
        exe_name = "elevated_process"

    return exe_name, title


class WindowPoller:
    """
    Background thread that polls the active window and emits WindowChangeEvents.

    One WindowChangeEvent is emitted per session boundary (i.e. whenever the
    focused exe or window title changes). The event carries both the closing
    session info (prev_*) and the opening session info (new_*) so the
    DatabaseWriter can handle them atomically.
    """

    def __init__(
        self,
        window_queue: queue.Queue[WindowChangeEvent],
        shared_state: SharedState,
        stop_event: threading.Event,
        config: Config,
        categorizer: Categorizer,
    ) -> None:
        self._queue = window_queue
        self._state = shared_state
        self._stop = stop_event
        self._config = config
        self._categorizer = categorizer
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="WindowPoller"
        )

    def start(self) -> None:
        self._thread.start()

    def _poll_loop(self) -> None:
        last_exe: str | None = None
        last_title: str | None = None
        session_start = time.time()

        while not self._stop.is_set():
            try:
                exe, title = get_active_window()
                now = time.time()

                if exe != last_exe or title != last_title:
                    category = self._categorizer.categorize(exe, title)
                    event = WindowChangeEvent(
                        prev_exe=last_exe,
                        prev_title=last_title,
                        new_exe=exe,
                        new_title=title,
                        prev_start=session_start,
                        change_ts=now,
                        category=category,
                    )
                    try:
                        self._queue.put(event, block=True, timeout=0.5)
                    except queue.Full:
                        logger.warning("Window queue full — dropping event")

                    last_exe = exe
                    last_title = title
                    session_start = now

            except Exception:
                logger.exception("Unexpected error in WindowPoller")

            self._stop.wait(timeout=self._config.poll_interval_sec)

        # Emit a final close event so the last open session is written to DB
        if last_exe is not None:
            now = time.time()
            try:
                self._queue.put(
                    WindowChangeEvent(
                        prev_exe=last_exe,
                        prev_title=last_title,
                        new_exe="",
                        new_title="",
                        prev_start=session_start,
                        change_ts=now,
                        category="",
                    ),
                    block=False,
                )
            except queue.Full:
                pass
