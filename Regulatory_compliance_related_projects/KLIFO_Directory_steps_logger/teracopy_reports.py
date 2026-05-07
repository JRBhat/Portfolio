"""Helpers for locating TeraCopy transfer reports.

TeraCopy writes simple text reports to a directory; this module helps find the
most-recent report file so the watcher can reference it when finalising copy
sessions.
"""

from pathlib import Path
from typing import Optional


class TeraCopyReportFinder:
    """Locate TeraCopy report files in a configured directory.

    Parameters
    ----------
    reports_dir:
        Directory where TeraCopy stores its .txt report files.
    timeout:
        Timeout (in seconds) used by callers when making inactivity decisions.
    """

    def __init__(self, reports_dir: Path, timeout: int):
        self.reports_dir = reports_dir
        self.timeout = timeout


    def find_latest_report(self) -> Optional[str]:
        """Return the path to the most recently modified report file or `None`.

        Returns
        -------
        Optional[str]
            Absolute path string to the latest report, or `None` if there are no
            `.txt` files in `reports_dir`.
        """
        reports = list(self.reports_dir.glob("*.txt"))
        if not reports:
            return None
        latest = max(reports, key=lambda f: f.stat().st_mtime)
        return str(latest) 