# file_finders.py
from pathlib import Path
import re
from datetime import datetime


def find_latest_user_file(folder: Path, pattern_suffix: str = ".xlsx"):
    """
    Search folder for files matching *_YYYYMMDD_HHMMSS.xlsx.
    Return Path to latest file or None if none found.
    """
    if not folder or not folder.exists():
        return None

    candidates = []
    for p in folder.glob(f"*{pattern_suffix}"):
        # Expect name like: prefix_YYYYMMDD_HHMMSS.xlsx
        m = re.search(r"_(\d{8})_(\d{6})$", p.stem)  # match end of stem
        if not m and "missing" not in p.stem.lower():
            continue
        try:
            dt = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
        except Exception:
            continue
        candidates.append((dt, p))

    if not candidates:
        return None

    # return path with greatest dt
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]