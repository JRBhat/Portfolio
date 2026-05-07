"""
Daily summary report generator.

Reads from the SQLite database (read-only connection) and renders a
rich-formatted report to the terminal. Produces two sections:

1. Daily Summary  — totals, per-app ranking, productivity breakdown bar
2. Time Trail     — chronological activity timeline (optional, --trail flag)
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import Config
from .database import Database

logger = logging.getLogger(__name__)

# ── Visual constants ──────────────────────────────────────────────────────────

_CATEGORY_STYLE: dict[str, str] = {
    "work":    "bold green",
    "leisure": "yellow",
    "system":  "dim",
    "unknown": "cyan",
}
_BAR_WIDTH = 28
_MAX_TITLE_LEN = 55


class Reporter:
    """
    Generates daily activity reports from the activity database.

    Call generate() once per report request. It handles missing/empty data
    gracefully so it is safe to run even before any tracking session has ended.
    """

    def __init__(self, config: Config) -> None:
        self._db = Database(config.db_path)
        self._console = Console()

    def generate(
        self,
        date_str: str | None = None,
        show_trail: bool = False,
        trail_from: str | None = None,
        trail_to: str | None = None,
    ) -> None:
        """
        Render a daily report for the given date (default: today).

        Args:
            date_str:   ISO date string "YYYY-MM-DD". Defaults to today.
            show_trail: If True, append a chronological time trail.
            trail_from: Optional start time filter "HH:MM" for the trail.
            trail_to:   Optional end time filter "HH:MM" for the trail.
        """
        date = date_str or datetime.date.today().isoformat()

        try:
            sessions = self._db.query_window_sessions(date)
            inputs = self._db.query_input_totals(date)
            idles = self._db.query_idle_periods(date)
        except FileNotFoundError as exc:
            self._console.print(f"[red]{exc}[/red]")
            return

        if not sessions:
            self._console.print(
                f"[yellow]No activity recorded for {date}.[/yellow]\n"
                "Make sure the tracker is running: [bold]pixi run start[/bold]"
            )
            return

        total_active, total_idle = _compute_times(sessions, idles)

        self._render_header(date)
        self._render_summary(total_active, total_idle, inputs)
        self._render_app_table(sessions, total_active)
        self._render_productivity_bars(sessions, total_active)

        if show_trail:
            self._render_trail(date, trail_from, trail_to)

    # ── Section renderers ─────────────────────────────────────────────────────

    def _render_header(self, date: str) -> None:
        self._console.print()
        self._console.print(
            Panel(
                f"[bold cyan]WorkTime Report  —  {date}[/bold cyan]",
                box=box.DOUBLE,
                expand=False,
            )
        )

    def _render_summary(
        self,
        total_active: float,
        total_idle: float,
        inputs: dict[str, float],
    ) -> None:
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column("Label", style="dim", min_width=16)
        table.add_column("Value", style="bold")

        table.add_row("Active time",  _fmt_duration(total_active))
        table.add_row("Idle time",    _fmt_duration(total_idle))
        table.add_row("Keystrokes",   f"{int(inputs['total_keys']):,}")
        table.add_row("Mouse clicks", f"{int(inputs['total_clicks']):,}")

        self._console.print(Panel(table, title="Summary", border_style="cyan"))

    def _render_app_table(
        self, sessions: list[dict[str, Any]], total_active: float
    ) -> None:
        per_app = _aggregate_by_app(sessions)
        ranked = sorted(per_app.items(), key=lambda x: -x[1][0])

        table = Table(box=box.SIMPLE_HEAD, show_lines=False, padding=(0, 1))
        table.add_column("#",            style="dim",       width=4,  justify="right")
        table.add_column("Application",  style="bold",      min_width=22)
        table.add_column("Category",     width=10)
        table.add_column("Time",         width=10,          justify="right")
        table.add_column("%",            width=6,           justify="right")

        for rank, (exe, (duration, category)) in enumerate(ranked, start=1):
            pct = (duration / total_active * 100) if total_active > 0 else 0
            table.add_row(
                str(rank),
                exe,
                Text(category, style=_CATEGORY_STYLE.get(category, "white")),
                _fmt_duration(duration),
                f"{pct:.0f}%",
            )

        self._console.print(
            Panel(table, title="Top Applications", border_style="cyan")
        )

    def _render_productivity_bars(
        self, sessions: list[dict[str, Any]], total_active: float
    ) -> None:
        per_cat: dict[str, float] = {}
        for s in sessions:
            if s["end_ts"] is None:
                continue
            dur = s["end_ts"] - s["start_ts"]
            per_cat[s["category"]] = per_cat.get(s["category"], 0.0) + dur

        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        table.add_column("Category", style="dim", width=10)
        table.add_column("Bar",      min_width=_BAR_WIDTH)
        table.add_column("Pct",      width=5, justify="right")

        for cat in ("work", "leisure", "system", "unknown"):
            dur = per_cat.get(cat, 0.0)
            pct = (dur / total_active * 100) if total_active > 0 else 0.0
            filled = int(pct / 100 * _BAR_WIDTH)
            bar = "█" * filled + "░" * (_BAR_WIDTH - filled)
            style = _CATEGORY_STYLE.get(cat, "white")
            table.add_row(
                cat.capitalize(),
                Text(bar, style=style),
                f"{pct:.0f}%",
            )

        self._console.print(
            Panel(table, title="Productivity Breakdown", border_style="cyan")
        )

    def _render_trail(
        self,
        date: str,
        trail_from: str | None,
        trail_to: str | None,
    ) -> None:
        from_ts = _parse_hhmm(date, trail_from) if trail_from else None
        to_ts   = _parse_hhmm(date, trail_to)   if trail_to   else None

        try:
            events = self._db.query_trail(date, from_ts, to_ts)
        except FileNotFoundError as exc:
            self._console.print(f"[red]{exc}[/red]")
            return

        if not events:
            self._console.print(
                "[yellow]No trail events in the specified window.[/yellow]"
            )
            return

        window_label = ""
        if trail_from or trail_to:
            window_label = f"  [{trail_from or '00:00'} – {trail_to or 'now'}]"

        table = Table(box=box.SIMPLE_HEAD, show_lines=False, padding=(0, 1))
        table.add_column("Start",        width=10)
        table.add_column("Application",  style="bold", min_width=22)
        table.add_column("Category",     width=10)
        table.add_column("Window Title", min_width=30)
        table.add_column("Duration",     width=10, justify="right")

        for ev in events:
            start_str = _ts_to_hms(ev["start_ts"])
            end_ts = ev["end_ts"]
            dur_str = (
                _fmt_duration(end_ts - ev["start_ts"])
                if end_ts is not None
                else Text("ongoing", style="dim italic")
            )

            if ev["type"] == "idle":
                table.add_row(
                    Text(start_str, style="dim"),
                    Text("─ IDLE ─", style="dim italic"),
                    Text("", style="dim"),
                    Text("", style="dim"),
                    Text(dur_str if isinstance(dur_str, str) else "ongoing",
                         style="dim"),
                )
            else:
                raw_title = ev["window_title"]
                title = (
                    raw_title[: _MAX_TITLE_LEN] + "…"
                    if len(raw_title) > _MAX_TITLE_LEN
                    else raw_title
                )
                cat = ev["category"]
                table.add_row(
                    start_str,
                    ev["exe_name"],
                    Text(cat, style=_CATEGORY_STYLE.get(cat, "white")),
                    title,
                    dur_str if isinstance(dur_str, str) else "ongoing",
                )

        self._console.print(
            Panel(
                table,
                title=f"Time Trail  —  {date}{window_label}",
                border_style="cyan",
            )
        )


# ── Module-level helpers ──────────────────────────────────────────────────────

def _aggregate_by_app(
    sessions: list[dict[str, Any]],
) -> dict[str, tuple[float, str]]:
    """Return {exe_name: (total_seconds, category)} for completed sessions."""
    per_app: dict[str, list] = {}
    for s in sessions:
        if s["end_ts"] is None:
            continue
        exe = s["exe_name"]
        dur = s["end_ts"] - s["start_ts"]
        if exe not in per_app:
            per_app[exe] = [0.0, s["category"]]
        per_app[exe][0] += dur
    return {k: (v[0], v[1]) for k, v in per_app.items()}


def _compute_times(
    sessions: list[dict[str, Any]],
    idles: list[dict[str, Any]],
) -> tuple[float, float]:
    active = sum(
        s["end_ts"] - s["start_ts"]
        for s in sessions
        if s["end_ts"] is not None
    )
    idle = sum(
        i["duration_sec"]
        for i in idles
        if i["duration_sec"] is not None
    )
    return active, idle


def _fmt_duration(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m:02d}m"


def _ts_to_hms(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def _parse_hhmm(date: str, time_str: str) -> float:
    """Convert "YYYY-MM-DD" + "HH:MM" into a Unix timestamp."""
    dt = datetime.datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M")
    return dt.timestamp()
