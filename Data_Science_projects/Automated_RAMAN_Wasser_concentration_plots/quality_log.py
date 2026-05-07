"""
Shared quality-log writer for the Raman water-concentration pipelines.

Provides the ``QualityLog`` class used by both the 2D and 3D heatmap
scripts to accumulate structured log messages and write them to a
timestamped text file.
"""

import datetime
from pathlib import Path


class QualityLog:
    """
    Accumulate INFO/WARN log lines and write them to a timestamped file.

    Parameters
    ----------
    output_dir : str or Path
        Directory where the log file will be written.
    script_label : str
        Human-readable label for the script (appears in the log header).
    input_path : str or Path
        Path to the input data file (appears in the log header).
    header_notes : list of str, optional
        Additional note lines inserted between the ``Script`` line and the
        closing ``=``-rule in the written file.
    """

    def __init__(self, output_dir, script_label, input_path, header_notes=None):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = Path(output_dir) / f"data_quality_log_{ts}.txt"
        self._script_label = script_label
        self._input_path = input_path
        self._header_notes = header_notes or []
        self._lines = []
        self._nwarn = 0
        self._ninfo = 0

    def _append(self, line):
        self._lines.append(line)
        print(line)

    def header(self, title):
        sep = "=" * 70
        self._append(f"\n{sep}")
        self._append(f"  {title}")
        self._append(sep)

    def info(self, msg):
        self._lines.append(f"  INFO  {msg}")
        self._ninfo += 1

    def global_info(self, msg):
        self._append(f"  INFO  {msg}")
        self._ninfo += 1

    def warn(self, subj, prod, tp, msg):
        line = f"  WARN  [{subj} {prod} {tp}]  {msg}"
        self._append(line)
        self._nwarn += 1

    def note(self, msg):
        self._append(f"  {msg}")

    def write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        note_lines = [f"  NOTE      : {n}" for n in self._header_notes]
        header_lines = [
            "=" * 70,
            f"  DATA QUALITY LOG  --  {self._script_label}",
            f"  Generated : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Script    : {Path(__file__).name}",
            f"  Input     : {self._input_path}",
        ] + note_lines + [
            "=" * 70,
        ]
        footer_lines = [
            "",
            "=" * 70,
            f"  TOTALS:  {self._nwarn} warning(s),  {self._ninfo} info message(s)",
            "=" * 70,
        ]
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(header_lines + self._lines + footer_lines))
            fh.write("\n")
        print(f"\n  Log written -> {self.path}")
        print(f"  Total: {self._nwarn} warning(s), {self._ninfo} info message(s)\n")
