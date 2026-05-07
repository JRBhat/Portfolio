"""
WorkTime Observer Logger — CLI entry point.

Commands:
  start          Start tracking in the foreground (Ctrl+C or 'worktime stop' to quit)
  stop           Stop a running tracker instance via stop-flag file
  report         Print the daily summary report
    --date       Date to report (YYYY-MM-DD, default: today)
    --trail      Append a chronological time trail to the report
    --from HH:MM Filter trail to start at this time
    --to   HH:MM Filter trail to end at this time

Run via pixi tasks:
  pixi run start
  pixi run stop
  pixi run report
"""
from __future__ import annotations

import argparse
import logging
import sys
import time


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


# ── Command handlers ──────────────────────────────────────────────────────────

def cmd_start(args: argparse.Namespace) -> None:
    """Start the tracker in the foreground and block until stopped."""
    from tracker.config import Config
    from tracker.session_manager import SessionManager, read_pid

    _setup_logging()
    config = Config.load()

    # Refuse to start a second instance
    existing_pid = read_pid(config.pid_file)
    if existing_pid is not None:
        print(
            f"[WorkTime] Tracker already running (PID {existing_pid}).\n"
            "Run 'pixi run stop' to stop it first.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Clear any stale stop-flag from a previous crashed run
    config.stop_flag_file.unlink(missing_ok=True)

    manager = SessionManager(config)
    manager.start()
    print(
        "[WorkTime] Tracking started.\n"
        "  Press Ctrl+C  or run  'pixi run stop'  to stop.\n"
        f"  Data: {config.db_path}"
    )

    try:
        manager.join()   # blocks until stop-flag or KeyboardInterrupt
    except KeyboardInterrupt:
        print("\n[WorkTime] Interrupted.")
    finally:
        manager.stop()
        print("[WorkTime] Stopped. Run 'pixi run report' to see your activity.")


def cmd_stop(args: argparse.Namespace) -> None:
    """Write the stop-flag file and wait for the tracker to exit."""
    from tracker.config import Config
    from tracker.session_manager import read_pid

    config = Config.load()
    pid = read_pid(config.pid_file)

    if pid is None:
        print("[WorkTime] No running tracker found.", file=sys.stderr)
        sys.exit(1)

    print(f"[WorkTime] Sending stop signal to PID {pid}...")
    config.stop_flag_file.write_text("stop", encoding="utf-8")

    # Wait up to 10 s for the PID file to disappear
    deadline = time.time() + 10.0
    while time.time() < deadline:
        if not config.pid_file.exists():
            print("[WorkTime] Tracker stopped.")
            return
        time.sleep(0.5)

    print(
        "[WorkTime] Tracker did not stop within 10 s. "
        "You may need to kill it manually.",
        file=sys.stderr,
    )


def cmd_report(args: argparse.Namespace) -> None:
    """Generate and print the daily activity report."""
    from tracker.config import Config
    from tracker.reporter import Reporter

    config = Config.load()
    reporter = Reporter(config)
    reporter.generate(
        date_str=args.date,
        show_trail=args.trail,
        trail_from=args.from_time,
        trail_to=args.to_time,
    )


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="worktime",
        description="Personal desktop activity tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # start
    sub.add_parser("start", help="Begin tracking (runs in foreground)")

    # stop
    sub.add_parser("stop", help="Stop a running tracker instance")

    # report
    rep = sub.add_parser("report", help="Print daily summary report")
    rep.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        default=None,
        help="Date to report (default: today)",
    )
    rep.add_argument(
        "--trail",
        action="store_true",
        default=False,
        help="Append a chronological time trail to the report",
    )
    rep.add_argument(
        "--from",
        dest="from_time",
        metavar="HH:MM",
        default=None,
        help="Filter time trail to start at this time",
    )
    rep.add_argument(
        "--to",
        dest="to_time",
        metavar="HH:MM",
        default=None,
        help="Filter time trail to end at this time",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    dispatch = {
        "start":  cmd_start,
        "stop":   cmd_stop,
        "report": cmd_report,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
