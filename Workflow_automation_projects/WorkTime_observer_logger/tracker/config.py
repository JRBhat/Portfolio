"""Application configuration — paths and tunable thresholds."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """
    All file paths and tunable parameters for the tracker.

    Use Config.load() to create an instance with sensible defaults
    pointing to %APPDATA%\\WorkTimeObserver\\.
    """

    db_path: Path
    pid_file: Path
    stop_flag_file: Path

    # ── Tunable thresholds ────────────────────────────────────────────────────
    idle_threshold_sec: int = 300       # 5 min of no input → idle
    poll_interval_sec: float = 1.0      # how often to check active window
    input_bucket_sec: int = 60          # flush input counts every N seconds
    min_session_sec: float = 2.0        # ignore window flashes shorter than this

    # ── Privacy settings ──────────────────────────────────────────────────────
    redact_title_exes: frozenset[str] = field(default_factory=frozenset)
    # e.g. frozenset({"chrome.exe", "outlook.exe"}) to hide window titles

    @classmethod
    def load(cls) -> Config:
        """
        Build config from environment, creating the data directory if needed.

        Data is stored in %APPDATA%\\WorkTimeObserver\\ and the directory ACLs
        are tightened so only the current user can access it.
        """
        base = Path(os.environ.get("APPDATA", Path.home())) / "WorkTimeObserver"
        base.mkdir(parents=True, exist_ok=True)
        _restrict_directory(base)
        return cls(
            db_path=base / "activity.db",
            pid_file=base / "tracker.pid",
            stop_flag_file=base / "tracker.stop",
        )


def _restrict_directory(path: Path) -> None:
    """
    Apply restrictive ACLs to the data directory on Windows.

    Removes inherited permissions and grants full control only to the current
    user, so no other local account can read the activity database.
    This is best-effort: tracker still works if icacls is unavailable.
    """
    username = os.environ.get("USERNAME", "")
    if not username:
        return
    try:
        subprocess.run(
            [
                "icacls",
                str(path),
                "/inheritance:r",
                "/grant:r",
                f"{username}:(OI)(CI)F",
            ],
            capture_output=True,
            check=False,
        )
    except OSError:
        pass
